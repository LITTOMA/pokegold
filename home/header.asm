; rst vectors (called through the rst instruction)

SECTION "rst0", ROM0[$0000]
	di
	jp Start

SECTION "rst8", ROM0[$0008]
FarCall::
	jp FarCall_hl

SECTION "rst10", ROM0[$0010]
Bankswitch::
	ldh [hROMBank], a
	ld [rROMB], a
	ret

SECTION "rst18", ROM0[$0018]
	rst $38

SECTION "rst20", ROM0[$0020]
	rst $38

SECTION "rst28", ROM0[$0028]
JumpTable::
	push de
	ld e, a
	ld d, 0
	add hl, de
	add hl, de
	ld a, [hli]
	ld h, [hl]
; SECTION "rst30", ROM0[$0030]
	ld l, a
	pop de
	jp hl

SECTION "rst38", ROM0[$0038]
	rst $38


; Game Boy hardware interrupts

SECTION "vblank", ROM0[$0040]
	jp VBlank

SECTION "lcd", ROM0[$0048]
	jp LCD

SECTION "timer", ROM0[$0050]
	reti

SECTION "serial", ROM0[$0058]
	jp Serial

SECTION "joypad", ROM0[$0060]
	jp Joypad

SECTION "Chinese Text Printer", ROM0[$0063]

ChineseChar:
	sub '<CN>'
	ldh [hChineseGlyphIndex + 1], a
	inc de
	ld a, [de]
	ldh [hChineseGlyphIndex], a
	push de
	push hl
	callfar GetChineseFontTile
	pop hl
	ldh a, [hChineseGlyphTile]
	ld [hli], a
	inc a
	ld [hli], a
	push hl
	ld bc, SCREEN_WIDTH - 2
	add hl, bc
	inc a
	ld [hli], a
	inc a
	ld [hl], a
	pop hl
	push hl
	ld bc, wAttrmap - wTilemap - 2
	add hl, bc
	ldh a, [hChineseFontInvert]
	and a
	ld a, BG_ATTR_VRAM_BANK_1
	jr nz, .got_attr
	ld a, PAL_BG_TEXT | BG_ATTR_VRAM_BANK_1
.got_attr
	ld [hli], a
	ld [hli], a
	ld bc, SCREEN_WIDTH - 2
	add hl, bc
	ld [hli], a
	ld [hl], a
	ldh a, [rLCDC]
	bit B_LCDC_ENABLE, a
	call nz, CGBOnly_CopyTilemapAtOnce
	pop hl
	pop de
	call PrintLetterDelay
	jp NextChar

INCLUDE "home/text_command_strings.asm"

SECTION "Header", ROM0[$0100]

Start::
; Nintendo requires all Game Boy ROMs to begin with a nop ($00) and a jp ($C3)
; to the starting address.
	nop
	jp _Start

; The Game Boy cartridge header data is patched over by rgbfix.
; This makes sure it doesn't get used for anything else.

	ds $0150 - @, $00

ENDSECTION

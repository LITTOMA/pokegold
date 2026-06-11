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
	inc de
	ld a, [de]
	add a
	add a
	add CHINESE_FONT_TILE_START
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
	push de
	ld bc, wAttrmap - wTilemap - 2
	add hl, bc
	ld a, PAL_BG_TEXT | BG_ATTR_VRAM_BANK_1
	ld [hli], a
	ld [hli], a
	ld bc, SCREEN_WIDTH - 2
	add hl, bc
	ld [hli], a
	ld [hl], a
	call CGBOnly_CopyTilemapAtOnce
	pop de
	pop hl
	call PrintLetterDelay
	jp NextChar

Request1bppVBank1::
; Load 1bpp at b:de to occupy c tiles of hl in VRAM bank 1.
	ldh a, [hBGMapMode]
	push af
	xor a
	ldh [hBGMapMode], a

	ldh a, [hROMBank]
	push af
	ld a, b
	rst Bankswitch

	ld a, e
	ld [wRequested1bppSource], a
	ld a, d
	ld [wRequested1bppSource + 1], a
	ld a, l
	ld [wRequested1bppDest], a
	ld a, h
	ld [wRequested1bppDest + 1], a
.loop
	ld a, c
	cp TILES_PER_CYCLE
	jr nc, .cycle

	or REQUEST_1BPP_VRAM_BANK_1
	ld [wRequested1bppSize], a
	call DelayFrame

	pop af
	rst Bankswitch

	pop af
	ldh [hBGMapMode], a
	ret

.cycle
	ld a, TILES_PER_CYCLE | REQUEST_1BPP_VRAM_BANK_1
	ld [wRequested1bppSize], a

	call DelayFrame
	ld a, c
	sub TILES_PER_CYCLE
	ld c, a
	jr .loop


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

GetChineseFontTile::
; Cache the current Chinese glyph in VRAM bank 1 and store its tile id.
	ldh a, [hChineseFontCacheInitialized]
	and a
	jr nz, .cache_ready
	call InitChineseFontCache
.cache_ready
	ldh a, [hChineseGlyphIndex]
	ld e, a
	ldh a, [hChineseGlyphIndex + 1]
	ld d, a
	ld hl, wChineseFontCache
	ld c, 0
	ld b, CHINESE_FONT_CACHE_CHARS
.search
	ld a, [hl]
	cp e
	jr nz, .next
	inc hl
	ld a, [hld]
	cp d
	jr z, .hit
.next
	inc hl
	inc hl
	inc c
	dec b
	jr nz, .search

	ldh a, [hChineseFontCacheNext]
	ld c, a
	ld a, c
	inc a
	and CHINESE_FONT_CACHE_CHARS - 1
	ldh [hChineseFontCacheNext], a
	ld h, 0
	ld l, c
	add hl, hl
	ld de, wChineseFontCache
	add hl, de
	ldh a, [hChineseGlyphIndex]
	ld [hli], a
	ldh a, [hChineseGlyphIndex + 1]
	ld [hl], a
	push bc
	call LoadChineseGlyph
	pop bc
.hit
	ld a, c
	add a
	add a
	add CHINESE_FONT_TILE_START
	ldh [hChineseGlyphTile], a
	ret

LoadChineseGlyph:
; Load the current Chinese glyph index into cache slot c in VRAM bank 1.
	ldh a, [hChineseGlyphIndex]
	ld l, a
	ldh a, [hChineseGlyphIndex + 1]
	push af
	and 1
	ld h, a
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	pop af
	bit 1, a
	jr nz, .font1
	ld de, ChineseFont0
	ld a, BANK(ChineseFont0)
	jr .got_font
.font1
	ld de, ChineseFont1
	ld a, BANK(ChineseFont1)
.got_font
	ld b, a
	add hl, de
	push hl
	push bc
	ld h, 0
	ld l, c
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	ld bc, vTiles2 tile CHINESE_FONT_TILE_START
	add hl, bc
	pop bc
	pop de
	ld c, CHINESE_FONT_TILES_PER_CHAR
	jp Request1bppVBank1

Request1bppVBank1:
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
	ld a, 1
	ldh [hRequested1bppVBK], a
.loop
	ld a, c
	cp TILES_PER_CYCLE
	jr nc, .cycle

	ld [wRequested1bppSize], a
	call DelayFrame

	pop af
	rst Bankswitch

	pop af
	ldh [hBGMapMode], a
	ret

.cycle
	ld a, TILES_PER_CYCLE
	ld [wRequested1bppSize], a

	call DelayFrame
	ld a, c
	sub TILES_PER_CYCLE
	ld c, a
	jr .loop

InitChineseFontCache::
	xor a
	ldh [hChineseFontCacheNext], a
	ld hl, wChineseFontCache
	ld b, CHINESE_FONT_CACHE_CHARS * 2
	ld a, CHINESE_FONT_CACHE_EMPTY
.clear
	ld [hli], a
	dec b
	jr nz, .clear
	ld a, 1
	ldh [hChineseFontCacheInitialized], a
	ret

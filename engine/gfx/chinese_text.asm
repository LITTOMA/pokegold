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
	inc a
	cp CHINESE_FONT_CACHE_CHARS
	jr c, .next_cache_slot
	xor a
.next_cache_slot
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
	cp CHINESE_FONT_CACHE_LOW_CHARS
	jr c, .low_tile_id
	sub CHINESE_FONT_CACHE_LOW_CHARS
	add a
	add a
	add CHINESE_FONT_TILE_HIGH_START
	jr .store_tile_id
.low_tile_id
	add a
	add a
	add CHINESE_FONT_TILE_START
.store_tile_id
	ldh [hChineseGlyphTile], a
	ld a, 1
	ldh [hChineseLineActive], a
	ret

LoadChineseGlyph:
; Load the current Chinese glyph index into cache slot c in VRAM bank 1.
	ldh a, [hChineseGlyphIndex]
	ld l, a
	ldh a, [hChineseGlyphIndex + 1]
	ld b, a
	and 1
	ld h, a
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	ld a, b
	srl a
	and $3
	jr z, .font0
	dec a
	jr z, .font1
	dec a
	jr z, .font2
	ld de, ChineseFont3
	ld a, BANK(ChineseFont3) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.font0
	ld de, ChineseFont0
	ld a, BANK(ChineseFont0) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.font1
	ld de, ChineseFont1
	ld a, BANK(ChineseFont1) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.font2
	ld de, ChineseFont2
	ld a, BANK(ChineseFont2) | $80
	ldh [hRequested1bppVBK], a
	and $7f
.got_font
	ld b, a
	add hl, de
	push hl
	ld a, c
	cp CHINESE_FONT_CACHE_LOW_CHARS
	jr c, .low_cache_slot
	sub CHINESE_FONT_CACHE_LOW_CHARS
	ld c, a
	ld de, vTiles1
	jr .got_dest_base
.low_cache_slot
	ld de, vTiles2 tile CHINESE_FONT_TILE_START
.got_dest_base
	ld h, 0
	ld l, c
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, hl
	add hl, de
	pop de
	ldh a, [hChineseFontInvert]
	ldh [hRequested1bppInvert], a
	ld c, CHINESE_FONT_TILES_PER_CHAR
	jp Request1bpp

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

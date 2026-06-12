GetChineseFontTile::
; Cache the current Chinese glyph in VRAM bank 1 and store its tile id.
	ldh a, [hChineseFontCacheInitialized]
	and a
	jr nz, .cache_ready
	ldh a, [hChineseFontTownMap]
	and a
	jr nz, .init_town_map_cache
	call InitChineseFontCache
	jr .cache_ready
.init_town_map_cache
	call InitChineseTownMapFontCache
.cache_ready
	ldh a, [hChineseFontCacheNext]
	ld c, a
	inc a
	push af
	ldh a, [hChineseFontTownMap]
	and a
	pop af
	jr nz, .check_town_map_next
	cp CHINESE_FONT_CACHE_CHARS
	jr c, .next_cache_slot
	xor a
	jr .next_cache_slot
.check_town_map_next
	cp CHINESE_TOWN_MAP_FONT_CACHE_CHARS
	jr c, .next_cache_slot
	xor a
.next_cache_slot
	ldh [hChineseFontCacheNext], a
	push bc
	call LoadChineseGlyph
	pop bc
	ldh a, [hChineseFontTownMap]
	and a
	ld a, c
	jr nz, .town_map_tile_id
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
	jr .store_tile_id
.town_map_tile_id
	add a
	add a
	add CHINESE_FONT_TILE_HIGH_START
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
	push af
	ldh a, [hChineseFontTownMap]
	and a
	jr z, .use_normal_font
	pop af
	jr .town_map_font
.use_normal_font
	pop af
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
	jr .got_font
.town_map_font
	jr z, .town_map_font0
	dec a
	jr z, .town_map_font1
	dec a
	jr z, .town_map_font2
	ld de, ChineseTownMapFont3
	ld a, BANK(ChineseTownMapFont3) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.town_map_font0
	ld de, ChineseTownMapFont0
	ld a, BANK(ChineseTownMapFont0) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.town_map_font1
	ld de, ChineseTownMapFont1
	ld a, BANK(ChineseTownMapFont1) | $80
	ldh [hRequested1bppVBK], a
	and $7f
	jr .got_font
.town_map_font2
	ld de, ChineseTownMapFont2
	ld a, BANK(ChineseTownMapFont2) | $80
	ldh [hRequested1bppVBK], a
	and $7f
.got_font
	ld b, a
	add hl, de
	push hl
	ldh a, [hChineseFontTownMap]
	and a
	ld a, c
	jr nz, .town_map_cache_slot
	cp CHINESE_FONT_CACHE_LOW_CHARS
	jr c, .low_cache_slot
	sub CHINESE_FONT_CACHE_LOW_CHARS
	ld c, a
	ld de, vTiles1
	jr .got_dest_base
.low_cache_slot
	ld de, vTiles2 tile CHINESE_FONT_TILE_START
	jr .got_dest_base
.town_map_cache_slot
	ld de, vTiles1
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
	ld a, 1
	ldh [hChineseFontCacheInitialized], a
	ret

InitChineseTownMapFontCache::
	xor a
	ldh [hChineseFontCacheNext], a
	ld a, 1
	ldh [hChineseFontCacheInitialized], a
	ret

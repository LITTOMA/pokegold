TownMap_ConvertLineBreakCharacters:
	ld hl, wStringBuffer1
.loop
	ld a, [hl]
	cp '@'
	jr z, .end
	cp '<WBR>'
	jr z, .line_feed
	cp '<BSP>'
	jr z, .line_feed
	inc hl
	jr .loop

.line_feed
	ld [hl], '<LF>'

.end
	call .StringContainsChinese
	jr nc, .regular
	ld a, 1
	ldh [hChineseFontTownMap], a
	farcall InitChineseTownMapFontCache
	ld de, wStringBuffer1
	hlcoord 9, 0
	ld a, 1
	ldh [hChineseLineActive], a
	call PlaceStringContinue
	call ResetChineseFontCache
	xor a
	ldh [hChineseFontTownMap], a
	ret

.regular
	ld de, wStringBuffer1
	hlcoord 9, 0
	call PlaceString
	ret

.StringContainsChinese:
	ld hl, wStringBuffer1
.scan
	ld a, [hli]
	cp '@'
	jr z, .no_chinese
	cp '<CN>'
	jr c, .scan
	cp '<BSP>'
	jr nc, .scan
	scf
	ret
.no_chinese
	and a
	ret

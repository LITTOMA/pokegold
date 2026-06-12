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
	ld a, [wStringBuffer1]
	cp '<CN>'
	jr c, .regular
	cp '<BSP>'
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

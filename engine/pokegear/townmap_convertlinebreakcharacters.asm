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
	farcall InitChineseFontCache
	ld de, wStringBuffer1
	hlcoord 9, 0
	ld a, 1
	ldh [hChineseLineActive], a
	call PlaceStringContinue
	call ClearChineseLineMode
	ret

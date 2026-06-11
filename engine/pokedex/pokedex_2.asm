AnimateDexSearchSlowpoke:
	ld hl, .FrameIDs
	ld b, 25
.loop
	ld a, [hli]

	; Wrap around
	cp $fe
	jr nz, .ok
	ld hl, .FrameIDs
	ld a, [hli]
.ok

	ld [wDexSearchSlowpokeFrame], a
	ld a, [hli]
	ld c, a
	push bc
	push hl
	call DoDexSearchSlowpokeFrame
	pop hl
	pop bc
	call DelayFrames
	dec b
	jr nz, .loop
	xor a
	ld [wDexSearchSlowpokeFrame], a
	call DoDexSearchSlowpokeFrame
	ld c, 32
	call DelayFrames
	ret

.FrameIDs:
	; frame ID, duration
	db 0, 7
	db 1, 7
	db 2, 7
	db 3, 7
	db 4, 7
	db -2

DoDexSearchSlowpokeFrame:
	ld a, [wDexSearchSlowpokeFrame]
	ld hl, .SlowpokeSpriteData
	ld de, wShadowOAMSprite00
.loop
	ld a, [hli]
	cp -1
	ret z
	ld [de], a ; y
	inc de
	ld a, [hli]
	ld [de], a ; x
	inc de
	ld a, [wDexSearchSlowpokeFrame]
	ld b, a
	add a
	add b
	add [hl]
	inc hl
	ld [de], a ; tile id
	inc de
	ld a, [hli]
	ld [de], a ; attributes
	inc de
	jr .loop

.SlowpokeSpriteData:
	dbsprite  9, 11, 0, 0, $00, 0
	dbsprite 10, 11, 0, 0, $01, 0
	dbsprite 11, 11, 0, 0, $02, 0
	dbsprite  9, 12, 0, 0, $10, 0
	dbsprite 10, 12, 0, 0, $11, 0
	dbsprite 11, 12, 0, 0, $12, 0
	dbsprite  9, 13, 0, 0, $20, 0
	dbsprite 10, 13, 0, 0, $21, 0
	dbsprite 11, 13, 0, 0, $22, 0
	db -1

DisplayDexEntry:
	call ResetChineseFontCache
	ld a, $ff
	ldh [hChineseFontInvert], a
	call Pokedex_PlaceDexEntryMenuItems
	call GetPokemonName
	hlcoord 9, 2
	call PlaceString ; mon species
	ld a, [wTempSpecies]
	ld b, a
	call GetDexEntryPointer
	ld a, b
	push af
	hlcoord 9, 4
	call PlaceFarString ; dex species
	ld h, b
	ld l, c
	push de
; Print dex number
	hlcoord 2, 8
	ld a, $5c ; No
	ld [hli], a
	ld a, $5d ; .
	ld [hli], a
	ld de, wTempSpecies
	lb bc, PRINTNUM_LEADINGZEROS | 1, 3
	call PrintNum
; Check to see if we caught it.  Get out of here if we haven't.
	ld a, [wTempSpecies]
	dec a
	call CheckCaughtMon
	pop hl
	pop bc
	jp z, ResetChineseFontCache
	push hl
	push bc
	hlcoord 9, 6
	ld de, .HeightLabel
	call PlaceString
	hlcoord 9, 8
	ld de, .WeightLabel
	call PlaceString
	pop bc
	pop hl
; Get the height of the Pokemon.
	ld a, [wCurPartySpecies]
	ld [wCurSpecies], a
	inc hl
	ld a, b
	push af
	push hl
	call GetFarWord
	ld d, l
	ld e, h
	pop hl
	inc hl
	inc hl
	ld a, d
	or e
	jr z, .skip_height
	push hl
	push de
; Print the height, with two of the four digits in front of the decimal point
	ld hl, sp+0
	ld d, h
	ld e, l
	hlcoord 12, 6
	lb bc, 2, (2 << 4) | 4
	call PrintNum
; Replace the decimal point with a ft symbol
	hlcoord 14, 6
	ld [hl], $5e
	pop af
	pop hl

.skip_height
	pop af
	push af
	inc hl
	push hl
	dec hl
	call GetFarWord
	ld d, l
	ld e, h
	ld a, e
	or d
	jr z, .skip_weight
	push de
; Print the weight, with four of the five digits in front of the decimal point
	ld hl, sp+0
	ld d, h
	ld e, l
	hlcoord 11, 8
	lb bc, 2, (4 << 4) | 5
	call PrintNum
	pop de

.skip_weight
; Page
	lb bc, 6, SCREEN_WIDTH - 2
	hlcoord 2, 11
	call ClearBox
	hlcoord 1, 10
	ld bc, SCREEN_WIDTH - 1
	ld a, $61 ; horizontal divider
	call ByteFill
	; page number
	hlcoord 1, 9
	ld [hl], $55
	inc hl
	ld [hl], $55
	hlcoord 1, 10
	ld [hl], $56 ; P.
	inc hl
	ld a, [wPokedexStatus]
	add $57 ; 1
	ld [hl], a
	pop de
	pop af
	ld a, [wTempSpecies]
	ld b, a
	ld a, [wPokedexStatus]
	inc a
	ld c, a
	call GetDexEntryPagePointer
	hlcoord 2, 11
	ld a, b
	call PlaceFarString
	jp ResetChineseFontCache

.HeightLabel:
	db "高@"

.WeightLabel:
	db "重@"

Pokedex_PlaceDexEntryMenuItems:
	hlcoord 1, 16
	ld de, .Page
	call PlaceString
	hlcoord 6, 16
	ld de, .Area
	call PlaceString
	hlcoord 11, 16
	ld de, .Cry
	call PlaceString
	hlcoord 15, 16
	ld de, .Print
	call PlaceString
	ret

.Page:
	db "PAGE@"
.Area:
	db "AREA@"
.Cry:
	db "CRY@"
.Print:
	db "PRNT@"

POKeString: ; unreferenced
	db "#@"

GetDexEntryPointer:
; return dex entry pointer b:de
	push hl
	ld hl, PokedexDataPointerTable
	ld a, b
	dec a
	ld d, 0
	ld e, a
	add hl, de
	add hl, de
	ld e, [hl]
	inc hl
	ld d, [hl]
	rlca
	rlca
	maskbits NUM_DEX_ENTRY_BANKS
	add BANK("Pokedex Entries 001-064")
	ld b, a
	pop hl
	ret

GetDexEntryPagePointer:
	call GetDexEntryPointer
	push hl
	ld h, d
	ld l, e
; skip species name
.loop1
	ld a, b
	call GetFarByte
	inc hl
	cp '@'
	jr nz, .loop1
; skip height and weight
rept 4
	inc hl
endr
; skip page count
	inc hl
; if c != 1: skip entry
	dec c
	jr z, .done
; skip entry
.loop2
	ld a, b
	call GetFarByte
	inc hl
	cp '@'
	jr nz, .loop2

.done
	ld d, h
	ld e, l
	pop hl
	ret

GetDexEntryPageCount:
	call GetDexEntryPointer
	push hl
	ld h, d
	ld l, e
; skip species name
.loop
	ld a, b
	call GetFarByte
	inc hl
	cp '@'
	jr nz, .loop
; skip height and weight
rept 4
	inc hl
endr
	ld a, b
	call GetFarByte
	pop hl
	ret

INCLUDE "data/pokemon/dex_entry_pointers.asm"

#!/usr/bin/env sh
# shell functions I use for my data
# these can be used in combination to filter/extract data
# a lot of them use https://github.com/stedolan/jq, so I'd
# recommend getting a bit familiar with that

mal_list() {
	if [ -z "${MAL_USERNAME}" ]; then
		echo "Set the 'MAL_USERNAME' environment variable to your account name" >&2
		return 1
	fi
	TYPE="${1:-anime}"
	DIR="${MALEXPORT_DIR:-${HOME}/.local/share/malexport}"
	python3 -m malexport parse list -s "${DIR}/${MAL_USERNAME}/${TYPE}list.json" | jq -r
}

openentry() {
	CHOSEN="$(mal_list "${1}" | jq -r '"\(.id)|\(.title)"' | fzf)"
	[ -z "${CHOSEN}" ] && return 1
	ID="$(echo "${CHOSEN}" | cut -d'|' -f1)"
	python3 -m webbrowser -t "https://myanimelist.net/${1}/${ID}"
}

animefzf() {
	openentry 'anime'
}

mangafzf() {
	openentry 'manga'
}

# filters the mal_list down to a particular status type
# mal_status 'Plan to Watch'
# mal_status 'Plan to Read' manga
mal_status() {
	mal_list "${2:-anime}" | jq "select(.status == \"${1:-Completed}\")"
}

# e.g. mal_list 'Dropped' | mal_filter_unscored | mal_describe
mal_filter_unscored() {
	jq 'select(.score != 0)'
}

mal_filter_type() {
	jq "select(.media_type == \"${1:-Movie}\")"
}

mal_sort_blobs() {
	jq -s "sort_by(.\"${1:-score}\") | .[]"
}

mal_filter_genre() {
	local genre
	genre="${1?:Pass name of Genre as first argument}"
	jq "select(.genres | .[] | .name | contains(\"${genre}\"))"
}

mal_filter_airing_status() {
	jq "select(.airing_status == \"${1:-Currently Airing}\")"
}

# given blobs of objects, describes each
# can be used like "mal_status 'Plan to Watch' | mal_describe"
mal_describe() {
	jq -r '"\(.id) \(.title) (\(.season.year)) \(.status) \(.score)/10"'
}

# I use my PTW to track items that haven't aired yet
# This opens any aired entries that are still on my PTW
mal_open_aired() {
	mal_status 'Plan to Watch' | jq -r 'select(.airing_status != "Not Yet Aired") | .id' | sed 's#^#https://myanimelist.net/anime/#' | xargs -I {} sh -c 'python3 -m webbrowser -t "{}"'
}

mal_club() {
	local club
	club="${1?:Pass club id as first argument}"
	curl -s "https://api.jikan.moe/v4/clubs/${club}/relations" | jq '.data.anime[].mal_id' | sort
}

#!/usr/bin/env sh
# shell functions I use for my data
# these can be used in combination to filter/extract data
# a lot of them use https://github.com/stedolan/jq, so I'd
# recommend getting a bit familiar with that

if [ -z "${MAL_USERNAME}" ]; then
	echo "Set the 'MAL_USERNAME' environment variable to your account name"
fi

mal_list() {
	TYPE="${1:-anime}"
	malexport parse list "${MALEXPORT_DIR}/${MAL_USERNAME}/${TYPE}list.json" | jq -r '.entries | .[]'
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
# mal_status 'Plan to Watch' manga
mal_status() {
	mal_list "${2:-anime}" | jq "select(.status == \"${1:-Completed}\")"
}

# e.g. mal_list 'Dropped' | mal_filter_unscored | mal_describe
mal_filter_unscored() {
	jq 'select(.score != 0)'
}

# given blobs of objects, describes each
# can be used like "mal_status 'Plan to Watch' | mal_describe"
mal_describe() {
	jq -r '"\(.id) \(.title) (\(.season.year)) \(.status) \(.score)/10"'
}

# Opens any aired entries that are still on my PTW
mal_open_aired() {
	mal_status 'Plan to Watch' | jq -r 'select(.airing_status == "Currently Airing") | .id' | sed 's#^#https://myanimelist.net/anime/#' | xargs -I {} sh -c 'python3 -m webbrowser -t "{}"'
}

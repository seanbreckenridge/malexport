# should be used in bash/zsh
#	quite personal as it uses sources collated by my https://github.com/seanbreckenridge/mal-notify-bot
# this should be sourced into shell environment
#
# this lists any items that are currently on my 'Currently Watching'
# list which has a source (e.g., a youtube video) so I can watch it

# copy the sources down from my server
mal_sources_copy_vultr() {
	# cache this evry two hours with evry
	# https://github.com/seanbreckenridge/evry
	evry 2 hours -copy_mal_notify_sources && scp vultr:~/'code/mal-notify-bot/export.json' "${HOME}/.cache/source_cache.json"
}

# items on my CW
# use xml so its easier to update quickly
mal_sources_currently_watching_ids() {
	malexport parse xml "${MALEXPORT_DIR}/${MAL_USERNAME}"/animelist.xml | jq '.entries | .[] | select(.status == "Watching") | .anime_id' -r | sort
}

# items which have sources
mal_sources_has_sources() {
	jq -r 'keys[]' <"${HOME}/.cache/source_cache.json" | sort
}

# items on my CW which have a source
mal_sources_shared_ids() {
	comm -1 -2 <(mal_sources_has_sources) <(mal_sources_currently_watching_ids)
}

# extract an ID from the source file
mal_sources_extract_id() {
	local ID="${1?:Provide ID as first argument}"
	jq -r "to_entries | .[] | select(.key == \"$ID\") | .value" <"${HOME}/.cache/source_cache.json"
}

# copy down the sources file if needed
# pick a random ID on my currently watching I haven't watched yet
# start streaming the source(s) using mpv
mal_sources_watch_next() {
	mal_sources_copy_vultr
	local RANDOM_NEXT_ID
	if [[ -n "${RANDOM_MAL_ID}" ]]; then
		RANDOM_NEXT_ID="${RANDOM_MAL_ID}"
	else
		RANDOM_NEXT_ID="$(mal_sources_shared_ids | shuf -n1)"
	fi
	# marked done with https://github.com/z411/trackma/ curses interface
	mal_list | jq "select(.id == $RANDOM_NEXT_ID)" | mal_describe
	# https://sean.fish/d/extracturls?dark
	local urls="$(mal_sources_extract_id "${RANDOM_NEXT_ID}" | extracturls)"
	while IFS= read -r url; do
		# open the video in mpv https://sean.fish/d/mpv-corner?dark
		# https://sean.fish/d/stream-corner-480?dark
		# run behind tsp (a task spooler) so mpv waits till
		# previous is over
		echo "Source for ${RANDOM_NEXT_ID}: ${url}"
		CLIPBOARD_CONTENTS="${url}" stream-corner-480
	done <<<"$urls"
}

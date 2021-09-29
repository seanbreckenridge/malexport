# this updates list data
# source this file into your shell environment and
# then run mal_friends_update

mal_friends_list() {
	local JIKAN_URL="https://api.jikan.moe/v3/user/${MAL_USERNAME:?Set the MAL_USERNAME environment variable to your user}/friends"
	curl -s "${JIKAN_URL}" | jq -r '.friends | .[] | .username'
}

mal_friends_update() {
	while IFS= read -r user; do
		malexport update lists -u "${user}"
	done < <(mal_friends_list)
}

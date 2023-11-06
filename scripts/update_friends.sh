# this updates list data
# source this file into your shell environment and
# then run mal_friends_update

mal_friends_list() {
	malexport parse friends -u "$MAL_USERNAME" | jq '.[].username' -r
}

mal_update_user() {
	local user="$1"
	malexport update lists -u "${user}" -o anime
	malexport update lists -u "${user}" -o manga
}

mal_friends_update() {
	while IFS= read -r user; do
		mal_update_user "$user"
	done < <(mal_friends_list)
}

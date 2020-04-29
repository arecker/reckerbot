#!/bin/sh -e

log() {
    echo "seed.sh $1" 1>&2
}

export VAULT_ADDR="http://vault.local"
export VAULT_TOKEN="$(pass vault/root)"

export SECRET_PATH="secret/reckerbot"
export LOCAL_PATH="secrets/reckerbot.json"

log "fetching $SECRET_PATH"
data="$(vault kv get -format=json $SECRET_PATH | jq -r '.data.data')"

log "writing $LOCAL_PATH"
echo "$data" > "$LOCAL_PATH"

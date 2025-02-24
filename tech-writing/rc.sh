JIRA=https://jira.infinidat.com
WIKI=https://wiki.infinidat.com
#WIKI=https://wiki-test06.lab.gdc.il.infinidat.com

if [ -f ~/.tokens ] ; then
        . ~/.tokens
fi

if [ "$USER" = "" ] ; then
        read -p "user: " USER
        export USER
fi

if [ "$WIKI_TOKEN" = "" ] || [ "$JIRA_TOKEN" = "" ] ; then
        if [ "$PASS" = "" ] ; then
                read -s -p "$USER Wiki password: " PASS
                echo
                export PASS
        fi
fi

function verify_prerequisites {
        if [ "$(jq -r '.installed' <<< '{"installed":"Yes"}' 2>/dev/null)" = "" ] ; then
          echo "jq is not installed"
          exit
        fi

        if [ "$USER" = "root" ] ; then
          echo "Do not run $0 from root account"
          exit
        fi

        if [ "$USER" = "" ] ; then
                read -p "user: " USER
                export USER
        fi

        if [ "$WIKI_TOKEN" = "" ] || [ "$JIRA_TOKEN" = "" ] ; then
                if [ "$PASS" = "" ] ; then
                        read -s -p "$USER Wiki password: " PASS
                        echo
                        export PASS
                fi
        fi
}

function wiki {
        ACTION="$1"; shift
        API="$1"; shift
        RAWDATA="$1"; shift
        if [ "$WIKI_TOKEN" = "" ] ; then
                AUTH_USR="-u $USER:$PASS"
                AUTH_TKN=""
        else
                AUTH_USR=""
                AUTH_TKN="Authorization: Bearer $WIKI_TOKEN"
        fi
        if [ "$ACTION" = "GET" ] ; then
                curl -sS -k ${AUTH_USR} -H "$AUTH_TKN" -H "Content-Type: application/json" -X $ACTION  "$WIKI$API"
        else
                if [ "$RAWDATA" != "" ] ; then
                        curl -sS -k ${AUTH_USR} -H "$AUTH_TKN" -H "Content-Type: application/json" -X $ACTION  "$WIKI$API" -d "$RAWDATA$*"
                else

                        curl -sS -k ${AUTH_USR} -H "$AUTH_TKN" -H "Content-Type: application/json" -X $ACTION  "$WIKI$API" $*
                fi
        fi
}

function wiki_upload {
        API="$1"; shift
        if [ "$WIKI_TOKEN" = "" ] ; then
                AUTH_USR="-u $USER:$PASS"
                AUTH_TKN=""
        else
                AUTH_USR=""
                AUTH_TKN="Authorization: Bearer $WIKI_TOKEN"
        fi
        curl -sS -k  ${AUTH_USR} -H "$AUTH_TKN" -H "X-Atlassian-Token: no-check" -X POST "$WIKI$API" -F "file=@$1"
}

function wiki_download {
        DL="$1"; shift
        OUT="$1"; shift
        if [ "$WIKI_TOKEN" = "" ] ; then
                AUTH_USR="-u $USER:$PASS"
                AUTH_TKN=""
        else
                AUTH_USR=""
                AUTH_TKN="Authorization: Bearer $WIKI_TOKEN"
        fi
        curl -sS -k  ${AUTH_USR} -H "$AUTH_TKN" -H "X-Atlassian-Token: no-check" -X GET "$DL" --output "$OUT"
}


function jira {
	if [ "$JIRA_TOKEN" = "" ] ; then
			AUTH_USR="-u $USER:$PASS"
			AUTH_TKN=""
	else
			AUTH_USR=""
			AUTH_TKN="Authorization: Bearer $JIRA_TOKEN"
	fi
        curl -sS -k ${AUTH_USR} -H "$AUTH_TKN" -H "Content-Type: application/json" -X $1  "$JIRA$2" -d "$3"
}

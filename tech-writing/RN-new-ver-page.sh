#! /bin/bash

##############################################################################
# The script take the master page 
# https://wiki.infinidat.com/display/~gnadel/Release+Notes+Review+Process
# which has ID 71450622 (this is embedded in the script).
#
# It creates child pages with the same content, except it replaces the 
# CQL queries which contain NEWVER and OLDVER with the adjusted values from 
# the parameters.
##############################################################################

if [ "$(jq -r '.installed' <<< '{"installed":"Yes"}' 2>/dev/null)" = "" ] ; then
  echo "jq is not installed"
  exit
fi

if [ "$1" != "" ] ; then
  USER=$1
  shift
fi

if [ "$USER" = "" -o "$USER" = "root" ] ; then 
  read -p "user: " USER
fi

read -s -p "$USER password: " PASS
echo 

PAGEID=71450622

function CreateReleasePage() {
  prj=$1
  new=$2
  old=$3

  NEWVER2="^($(echo $new | sed 's#\.#\\\\\\\\\\\\\\\\.#g'))"
  OLDVER1="^($(echo $old | sed 's#\.#\\\\\\\\\\\\\\\\.#g' | sed 's#|#)|(#g' ))"
  OLDVER2="${OLDVER1//\\/\\\\}"
  PRJ=${prj//,/\\\&quot\\\;,\\\&quot\\\;}

  PAGE=$(curl -s -S -u $USER:$PASS -H "Content-Type: application/json" -X GET  "https://wiki.infinidat.com/rest/api/content/$PAGEID?expand=body.storage,space")
  SPACE=$(jq -r '.space.key' <<< $PAGE)
  BODY=$(jq '.body.storage.value' <<< $PAGE)
  NEWBODY=$(echo $BODY | sed "s#NEWVER1#$new#g"| sed "s#NEWVER2#$NEWVER2#g" | sed "s#OLDVER1#$OLDVER1#g" | sed "s#OLDVER2#$OLDVER2#g" | sed "s#DOC#$PRJ#g" )
  TITLE="RN process - $prj - $new"

  echo '{"type":"page","title":"'$TITLE'","space":{"key":"'$SPACE'"},"ancestors":[{"id":'$PAGEID'}],"body":{"storage":{"value":'$NEWBODY',"representation":"storage"}}}' | curl -s -S -u $USER:$PASS -H "Content-Type: application/json" -X POST  "https://wiki.infinidat.com/rest/api/content/" -d '@-'
}

##############################################################################
# Delete older release notes review pages
# Children of the master page
##############################################################################
OLDIDS=$(curl -s -S -u gnadel:Bassa005 -H 'Content-Type: application/json' -X GET "https://wiki.infinidat.com/rest/api/content/$PAGEID/child/page"  | jq -r '.results[] | .id')
for id in $OLDIDS; do
  curl -s -S -u $USER:$PASS -H "Content-Type: application/json" -X DELETE  "https://wiki.infinidat.com/rest/api/content/$id"
done

##############################################################################
# Extract release details (proj, new ver, old vers) from master page properties
##############################################################################
PAGE=$(curl -s -S -u $USER:$PASS -H "Content-Type: application/json" -X GET  "https://wiki.infinidat.com/rest/api/content/$PAGEID?expand=space")
SPACE=$(jq -r ".space.key" <<< $PAGE)
PROPERTIES=$(curl -s -S -u $USER:$PASS -H "Content-Type: application/json" -X GET  "https://wiki.infinidat.com/rest/masterdetail/1.0/detailssummary/lines?spaceKey=$SPACE&cql=ID=$PAGEID")

function getProp() {
PROPNUM=$(jq -r ".renderedHeadings[]" <<< $1 | grep -n $2 | awk -F: '{print $1}')
if [ "$PROPNUM" != "" ] ; then
jq -r ".detailLines[0].details[$(($PROPNUM-1))]" <<< $1 | html2text | head -1
fi
}

for ((i=1;i<100;i++)); do
  prj=$(getProp "$PROPERTIES" rel${i}proj)
  new=$(getProp "$PROPERTIES" rel${i}newver)
  old=$(getProp "$PROPERTIES" rel${i}oldver)
  if [ $"$prj" = "" ] ; then break; fi
  echo "$prj $new $old"
  CreateReleasePage "$prj" "$new" "$old"
  echo
done




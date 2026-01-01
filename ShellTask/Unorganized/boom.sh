#/bin/bash
docker run --rm lanqsh/smsboom run  -p 13067890704 -i 1 > boom.log 2>&1 &

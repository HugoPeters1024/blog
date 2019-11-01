#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo $DIR
cd $DIR
echo "Watching changes to design..."
while chronic inotifywait ../design -r -e modify; do 
  cd ..;
  chronic pipenv run blog build --debug;
  cd scripts;
done

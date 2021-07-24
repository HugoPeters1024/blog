# requires you hold the private key of the pi in question :)

pipenv run blog build
scp -r ./ignore/build/* pi@hugopeters.me:/var/www/blog

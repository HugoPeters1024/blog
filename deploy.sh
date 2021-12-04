# requires you hold the private key of the pi in question :)

pipenv run python main.py build
scp -r ./ignore/build/* pi@hugopeters.me:/var/www/blog

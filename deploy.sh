# requires you hold the private key of the pi in question :)

python3 main.py build
scp -r ./ignore/build/* pi@hugopeters.me:/var/www/blog

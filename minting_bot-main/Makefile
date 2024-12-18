run:
	docker run -it -d --env-file .env --restart=unless-stopped --name ton_bot ton_bot_image
stop:
	docker stop ton_bot
attach:
	docker attach ton_bot
dell:
	docker rm ton_bot
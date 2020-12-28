FROM python:3.7
WORKDIR /app
COPY . .
RUN [ "pip3", "install", "-r", "requirements.txt" ]
EXPOSE 1234
CMD [ "python3", "simplemud.py" ]
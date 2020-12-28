FROM python
WORKDIR /app
COPY . .
EXPOSE 1234
CMD [ "python", "simplemud.py" ]
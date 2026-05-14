FROM node:22.12-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

COPY .env.docker .env

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

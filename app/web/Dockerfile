FROM node:20-alpine

WORKDIR /app

# Manifest first so source edits do not invalidate the npm layer.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]

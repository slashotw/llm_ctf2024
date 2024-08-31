# llm_ctf2024 (beta)
> author: slasho.tw

## usage
1. put your api_key in docker-compose.yml
```
version: "3"

x-common-variables: &common-variables
  API_KEY: put your API_KEY here

services:
  prompt_injection:
    build:
      context: prompt_injection
      dockerfile: Dockerfile
...
```
2. use docker-compose to run all the container!
```
docker-compose up -d
```

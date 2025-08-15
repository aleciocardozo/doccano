# Expansão na Ferramenta Doccano para Análise de Sentimentos

Expansão da ferramenta Doccano dedicada a facilitar a criação de conjuntos de dados anotados para Análise de Sentimentos, com suporte para anotações manuais nos níveis de documento e aspecto.

## Pré-requisitos

- Docker
- Docker Compose

## Inicie a Aplicação via Docker Compose

Após clonar o repositório, você precisa entrar na pasta principal do projeto para iniciar a aplicação.

### Entre na pasta do projeto

Primeiro, certifique-se de que você está dentro da pasta doccano.

```bash
$ cd doccano
```

### Verifique o arquivo de ambiente

O arquivo .env com o usuário e a senha já estão incluídos. Se desejar, você pode abri-lo dentro da pasta docker e alterar o nome de usuário (admin) ou a senha (password) do administrador.

### Inicie os containers

Em seguida, para executar o comando de inicialização, você precisa entrar na pasta docker.

```bash
$ cd docker
```

Agora, execute o comando abaixo para construir.

```bash
$ docker-compose -f docker-compose.prod.yml --env-file .env build
```

Depois de executar o comando acima, inicie os containers.

```bash
$ docker-compose -f docker-compose.prod.yml up
```

### Acesse a ferramenta

Após a inicialização completa, a ferramenta estará disponível no seu navegador em http://127.0.0.1/.
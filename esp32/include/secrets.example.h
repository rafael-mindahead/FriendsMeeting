
#pragma once

// Para que o ESP32 se conecte à rede Wi-Fi, você precisa definir o SSID e a senha da sua rede.
// Substitua "NOME_DA_REDE" e "SENHA_DA_REDE" pelos seus valores.

#define WIFI_SSID "NOME_DA_REDE"
#define WIFI_PASSWORD "SENHA_DA_REDE"

//Para definir o host e a porta do backend, primeiramente você precisa saber o endereço IP do computador que está rodando o backend.
//Você pode descobrir o IP utilizando o comando "ipconfig" no Windows ou "ifconfig" no Linux/Mac. O IP geralmente começa com 192.168.x.x ou 10.x.x.x. Na sessão de adaptador de rede sem fio, procure por "Endereço IPv4" ou "inet" para encontrar o IP do seu computador. Substitua "IP_DO_COMPUTADOR" pelo IP que você encontrou.
//Para descobrir a porta da API do backend, você pode rodar o comando "docker compose ps" no terminal, e nos cabeçalhos da tabela, procure por PORTS.
//A porta do backend é a definida embaixo do nome do serviço, no nosso caso "friendsmeeting-api". Por padrão, a porta do backend é 8000, mas caso você tenha alterado, utilize a porta que você definiu.

#define BACKEND_HOST "IP_DO_COMPUTADOR"
#define BACKEND_PORT "PORTA_DO_BACKEND"

// A chave do dispositivo ESP32 é uma chave única que identifica o seu dispositivo no backend.
#define ESP32_DEVICE_KEY "CHAVE_DO_DISPOSITIVO_ESP32"
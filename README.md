# ELC1017 - Redes de Computadores (2024)

Este repositório contém implementações e experimentos para a disciplina **ELC1017 - Redes de Computadores**. Os scripts apresentados modelam topologias de rede usando o **Mininet** e implementam protocolos de roteamento personalizados.

## Estrutura do Repositório

### Arquivos Principais

1. **`topology.py`**
   - Define diversas topologias de rede utilizando o framework Mininet:
     - `BasicTopo`: Uma topologia simples com um roteador e dois hosts.
     - `ThreeRoutersTopo`: Conecta três roteadores em série com dois hosts nas extremidades.
     - `TwoPathsTopo`: Conecta dois hosts com múltiplos caminhos possíveis através de switches.
     - `MeshTopo`: Uma malha totalmente conectada com quatro hosts e switches.
   - Implementa funções auxiliares para configuração inicial de tabelas de roteamento.
   - Permite iniciar a simulação via linha de comando.

2. **`routing.py`**
   - Implementa um protocolo de roteamento baseado em distância-vetor chamado **Table Routing Protocol (TRP)**.
   - Principais funcionalidades:
     - Compartilhamento periódico de tabelas de roteamento entre vizinhos.
     - Processamento de pacotes recebidos para atualizar a tabela de roteamento.
     - Encaminhamento de pacotes com base na tabela de roteamento.
   - Inclui ferramentas para exibir tabelas de roteamento e interfaces.

---

## Pré-requisitos

Antes de executar os scripts, certifique-se de ter o seguinte instalado:

- **Python 3.6+**
- **Mininet**
- **Scapy**
- 
### Instalação do Mininet

Siga o guia oficial para instalar o Mininet: [Mininet Installation](http://mininet.org/download/).

### Instalação do Scapy

Instale o Scapy utilizando o pip:

```bash
pip install scapy

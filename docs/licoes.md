# Lições da fábrica

Falhas reais de operação ou construção. Uma entrada por lição: o que falhou, o sinal que teria
pegado antes e a correção. Acumula, não sobrescreve.

## 2026-11-05: teste de fuga verde na primeira rodada, e parte dele não testava nada

**O que falhou:** 22 de 22 testes passaram de primeira. Ao enfraquecer o isolamento de propósito, o
teste de raiz somente leitura continuou verde, porque um usuário sem root já não escreve em `/usr`.
O de `cap-drop` só pegou porque passei a olhar `CapBnd`: em `CapEff`, sem root, é sempre zero. O do
proxy aceitava qualquer falha de `curl` e passava com o proxy parado.

**Sinal:** teste de segurança que nunca foi visto falhando não é evidência.

**Correção:** os testes conferem a causa exata (`/proc/mounts`, `CapBnd`, `http_connect` 403) e cada
proteção passou pelo sensor: removida, teste reprova, restaurada.

## 2026-11-05: limites da CLI só apareceram ao rodar o agente de verdade

**O que falhou:** a primeira rodada do avaliador deu 0 de 6 sem o revisor rodar. A CLI recusou
`$schema`, a API recusou `allOf` no topo do schema, o Opus 5.5 exigia CLI mais nova e a limpeza de
ambiente exigia `bubblewrap`. O avaliador saiu com exit 0 nessa rodada porque a saída passava por `cut`.

**Sinal:** schema de teste simplificado não prova que o schema real é aceito. Exit code visto através
de pipe não é o do comando.

**Correção:** `schema_para_cli` tira do envio o que a CLI e a API recusam, e a fábrica revalida com o
schema completo. Teste com os schemas reais dos contratos. Avaliador roda sem pipe.

## 2026-11-05: o revisor reprovou o caso que eu chamei de correto

**O que falhou:** `caso/correto` não testava retirada igual ao saldo, e o mutante `>=` sobrevivia. O
revisor estava certo, o gabarito estava errado.

**Sinal:** divergência entre revisor e gabarito pede leitura do achado antes de mexer em qualquer lado.

**Correção:** o caso ganhou o teste. O revisor não mudou.

## 2026-11-05: token colado errado e token exposto em print

**O que falhou:** duas tentativas salvaram algo que não era token, e um print da tela expôs um token
válido no chat. Foi revogado.

**Sinal:** processo que depende de copiar segredo à mão vai falhar ou vazar.

**Correção:** `scripts/gerar_token.py` captura o token sem área de transferência.

## 2026-11-05: Fase 1, falhas achadas pelos próprios testes

**O que falhou:**
- Escrevi no Dockerfile um hash do `gitleaks` sem conferir. O `sha256sum -c` barrou a imagem.
- Depois de CI reprovado, a correção reenviava a mesma branch com outro histórico, e o push era recusado.
- `gh pr checks --json` não existe no `gh` 2.45 do WSL. A execução real pausou em `CI_E2E`.
- Ao matar o processo, o contêiner do agente seguiria rodando com o token.
- A mutação de renomeio sobreviveu: o código era redundante, e faltava recusar caminho ambíguo.

**Sinal:** valor externo se copia da fonte oficial; comando de ferramenta se testa na versão instalada.

**Correção:** hash do arquivo oficial de checksums; branch por tentativa, sem force-push; status lido
de `gh pr view`; contêineres etiquetados e encerrados na retomada; caminho ambíguo recusado.

**Limite conhecido:** a fábrica usa o login do owner no `gh`. Um merge dela aparece como dele, então a
conferência de "quem aprovou a SDD" não distingue os dois. Um usuário próprio para a fábrica resolve.

## 2026-11-05: Fase 2, retomada e arquivamento

**O que falhou:** retomar o arquivamento recriava a branch, e o push era recusado por histórico diferente.
Um `*pathspecs` de exclusão ficou fora do comando do Docker porque a edição do texto não casou depois da
formatação, e só o linter acusou a variável sem uso.

**Sinal:** etapa com efeito no remoto precisa guardar o que já fez, para a retomada não repetir.

**Correção:** o número da PR de arquivamento fica nos dados da execução. Edição por script agora confere
com `assert` que o trecho existe.


## 2026-11-05: Fase 2, a fábrica real parou demais

**O que falhou:** na primeira rodada, duas de quatro SDDs simples não chegaram ao fim. Agentes citaram
comandos como evidência, e cada recusa gastou uma tentativa. O revisor parou por ambiguidade em entradas que
a SDD nem cita, como `None`. A SDD 0009 consumiu 3 tentativas e US$ 0,94 antes de parar.

**Sinal:** gate correto que para demais também é defeito. Regra conferida depois da resposta deve estar no
schema, onde o agente a enxerga antes de responder.

**Correção:** formato da evidência no schema, com campo próprio para comandos. O revisor só alega
especificação quando não dá para decidir se um critério foi cumprido. O conjunto de defeitos plantados
continuou em 6 de 6, e as duas SDDs passaram na tentativa 1, a 0009 por US$ 0,47.

**Limite conhecido:** um testador barrado ainda faz o desenvolvedor refazer tudo na tentativa seguinte, o que
gasta mais do que precisaria.

## 2026-11-05: Fase 3, comparação de decisores

**O que falhou:** a primeira rodada do Strands gravou 0 linhas: o cache sem rede guarda o modelo pela revisão
fixada, e o worker pedia `main`. O script mostrou `strands exit=0` porque o exit era o do `tail`, armadilha já
registrada aqui. No painel, atribuí a lentidão dos testes a `getfqdn` e commitei a correção sem medir. A
medição deu 2 ms; a causa era o SQLite com o disco ocupado pelo build. Desfiz antes de publicar.

**Sinal:** resultado ruim demais pede controle positivo antes de virar conclusão. Linhas gravadas são prova
melhor que exit visto através de pipe. Hipótese de desempenho se mede antes de virar comentário no código.

**Achado maior:** ler as regras para montar os casos mostrou que tarefas de autenticação e pagamento com
`sizing: small` saíam como risco baixo. Testes parametrizados cobriam só `login` e caminhos em inglês.

**Correção:** o worker carrega a revisão fixada, e o controle com o exemplo do autor separou defeito de uso de
fraqueza do modelo. Gabarito commitado antes da primeira resposta, para o resultado não influenciar os casos.

## 2026-11-05: release mergeada sem pós-release

**O que falhou:** o owner mergeou a release 0.4.0 enquanto eu trabalhava, e eu atualizei a release sem olhar o
estado da PR. Sem a tag, a fábrica calculou 0.4.0 de novo, avançou o ramo `release/0.4.0` já mergeado e abriu a
PR #11 com o número repetido. A pós-release também não servia: ela exige o ramo de release dentro de `main`, e
tentaria levar `develop` de volta a `main`, já com trabalho novo.

**Sinal:** etapa que depende de outra feita por humano precisa conferir se ela já aconteceu.

**Correção:** PR #11 fechada, tag `v0.4.0` criada no merge do owner. `preparar_release` recusa número de
release já contido em `main`, e a pós-release só move `develop` quando o fast-forward é possível.

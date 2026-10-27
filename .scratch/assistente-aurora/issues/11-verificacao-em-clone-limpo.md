# 11: Verificação em clone limpo

**What to build:** um avaliador que clona o fork consegue instalar, restaurar e subir a API seguindo só o README, e o repositório atende às checagens estáticas do passo 15. Nenhuma dessas verificações chama o modelo.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Num clone novo da branch, em diretório temporário, `uv sync` instala sem erro
- [ ] No clone novo, os comandos de restauração e subida do README deixam a API respondendo em `http://localhost:8000`, e o passo 1 passa: 101 lista `RSV-1377` e 302 lista Marina Duarte
- [ ] A versão exata do ADK está fixada (série 2, igual ou superior a 2.2.0) no `pyproject.toml` e no `uv.lock`
- [ ] Os arquivos de `dados/` são idênticos aos do repositório base (commit inicial do enunciado)
- [ ] Nenhuma chave nem `.env` está versionada em nenhum commit da branch, e o `.env.example` lista as variáveis sem valores
- [ ] Todo arquivo e intervalo de linhas citado na seção Garantias do README existe e mostra o trecho descrito

## Cómo levantar el proyecto (Docker)

Requisitos: Docker y Docker Compose. Todo el stack —Postgres, ChromaDB, la consola de
administración y el agente de voz— se levanta con un solo comando.

1. Copia `.env.example` a `.env` y completa `GOOGLE_API_KEY` y `DEEPGRAM_API_KEY`
   Para `DEEPGRAM_API_KEY` necesitas crear una cuenta gratuita en
   [Deepgram Console](https://console.deepgram.com/) y generar una API key desde ahí.
   Para `GOOGLE_API_KEY` obtén una key gratuita desde
   [Google AI Studio](https://aistudio.google.com/apikey).
2. Levanta todo:

   ```bash
   docker compose up --build
   ```

3. Espera a que los cuatro contenedores estén arriba (Postgres y ChromaDB tienen
   healthcheck; `api` corre las migraciones y siembra el dataset en Postgres
   automáticamente al iniciar).
4. Abre:
   - **Consola de administración** (subir/listar/eliminar documentos del RAG):
     http://localhost:8000
   - **Interfaz de llamada** (agente de voz por WebRTC): http://localhost:7860

La base de conocimiento clínico (`dataset/textos/`) no se ingesta automáticamente
—consume cuota de la API de embeddings de Gemini—; cárgala una vez desde la consola
de administración, o corre dentro del contenedor `agent`:

```bash
docker compose exec agent python -m agent.rag.ingest add-dir dataset/textos
```

Para bajar todo (conservando los datos en los volúmenes de Postgres/ChromaDB):

```bash
docker compose down
```
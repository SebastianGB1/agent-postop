const docTableBody = document.getElementById("doc-table-body");
const docCount = document.getElementById("doc-count");
const listStatus = document.getElementById("list-status");
const uploadForm = document.getElementById("upload-form");
const uploadStatus = document.getElementById("upload-status");
const refreshBtn = document.getElementById("refresh-btn");
const overlay = document.getElementById("detail-overlay");
const detailTitle = document.getElementById("detail-title");
const detailChunks = document.getElementById("detail-chunks");
const closeDetailBtn = document.getElementById("close-detail");

async function loadDocuments() {
  listStatus.textContent = "Cargando...";
  listStatus.classList.remove("error");
  try {
    const res = await fetch("/api/documents");
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const docs = await res.json();
    renderDocuments(docs);
    listStatus.textContent = "";
  } catch (err) {
    listStatus.textContent = `No se pudo cargar la lista: ${err.message}`;
    listStatus.classList.add("error");
  }
}

function renderDocuments(docs) {
  docCount.textContent = docs.length;
  docTableBody.innerHTML = "";

  for (const doc of docs) {
    const row = document.createElement("tr");
    row.className = "doc-row";

    const nameCell = document.createElement("td");
    nameCell.textContent = doc.filename;

    const countCell = document.createElement("td");
    countCell.textContent = doc.chunk_count;

    const actionCell = document.createElement("td");
    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "Eliminar";
    deleteBtn.className = "danger";
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteDocument(doc.doc_id, doc.filename);
    });
    actionCell.appendChild(deleteBtn);

    row.appendChild(nameCell);
    row.appendChild(countCell);
    row.appendChild(actionCell);
    row.addEventListener("click", () => openDetail(doc.doc_id));

    docTableBody.appendChild(row);
  }
}

async function openDetail(docId) {
  detailTitle.textContent = "Cargando...";
  detailChunks.innerHTML = "";
  overlay.classList.remove("hidden");

  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(docId)}`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const detail = await res.json();
    detailTitle.textContent = `${detail.filename} (${detail.doc_id})`;
    detailChunks.innerHTML = "";
    for (const chunk of detail.chunks) {
      const div = document.createElement("div");
      div.className = "chunk";

      const idDiv = document.createElement("div");
      idDiv.className = "chunk-id";
      idDiv.textContent = chunk.node_id;

      const textDiv = document.createElement("div");
      textDiv.textContent = chunk.text;

      div.appendChild(idDiv);
      div.appendChild(textDiv);
      detailChunks.appendChild(div);
    }
  } catch (err) {
    detailChunks.textContent = `No se pudo cargar el documento: ${err.message}`;
  }
}

async function deleteDocument(docId, filename) {
  if (!confirm(`Eliminar "${filename}" del indice?`)) return;

  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(docId)}`, {
      method: "DELETE",
    });
    if (!res.ok && res.status !== 204) throw new Error(`Error ${res.status}`);
    await loadDocuments();
  } catch (err) {
    listStatus.textContent = `No se pudo eliminar: ${err.message}`;
    listStatus.classList.add("error");
  }
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const file = fileInput.files[0];
  if (!file) return;

  uploadStatus.textContent = `Subiendo ${file.name}...`;
  uploadStatus.classList.remove("error");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/documents", { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    uploadStatus.textContent = `"${file.name}" indexado correctamente.`;
    uploadForm.reset();
    await loadDocuments();
  } catch (err) {
    uploadStatus.textContent = `No se pudo subir el archivo: ${err.message}`;
    uploadStatus.classList.add("error");
  }
});

refreshBtn.addEventListener("click", loadDocuments);
closeDetailBtn.addEventListener("click", () => overlay.classList.add("hidden"));
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) overlay.classList.add("hidden");
});

loadDocuments();

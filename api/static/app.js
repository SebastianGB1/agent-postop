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
const jobTableBody = document.getElementById("job-table-body");
const jobCount = document.getElementById("job-count");
const summaryTableBody = document.getElementById("summary-table-body");
const summaryCount = document.getElementById("summary-count");
const summaryStatus = document.getElementById("summary-status");
const refreshSummariesBtn = document.getElementById("refresh-summaries-btn");

const CLASIFICACION_LABELS = {
  verde: "Verde",
  amarillo: "Amarillo",
  rojo: "Rojo",
  sin_clasificar: "Sin clasificar",
};

const STATUS_LABELS = {
  pending: "Pendiente",
  processing: "Procesando",
  done: "Listo",
  error: "Error",
};

let pollHandle = null;
const notifiedDone = new Set();

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

function renderJobs(jobs) {
  jobCount.textContent = jobs.length;
  jobTableBody.innerHTML = "";

  let hasNewlyDone = false;

  for (const job of jobs) {
    if (job.status === "done" && !notifiedDone.has(job.job_id)) {
      notifiedDone.add(job.job_id);
      hasNewlyDone = true;
    }

    const row = document.createElement("tr");

    const nameCell = document.createElement("td");
    nameCell.textContent = job.filename;

    const statusCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge badge-${job.status}`;
    badge.textContent = STATUS_LABELS[job.status] || job.status;
    statusCell.appendChild(badge);

    if (job.status === "error" && job.error) {
      const errDiv = document.createElement("div");
      errDiv.className = "job-error";
      errDiv.textContent = job.error;
      statusCell.appendChild(errDiv);
    }

    row.appendChild(nameCell);
    row.appendChild(statusCell);
    jobTableBody.appendChild(row);
  }

  if (hasNewlyDone) loadDocuments();
}

async function refreshJobs() {
  try {
    const res = await fetch("/api/documents/uploads");
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const jobs = await res.json();
    renderJobs(jobs);

    const stillActive = jobs.some((j) => j.status === "pending" || j.status === "processing");
    if (stillActive) {
      startPolling();
    } else if (pollHandle) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  } catch {
    // Ignora fallos puntuales de polling; el proximo tick reintenta.
  }
}

function startPolling() {
  if (pollHandle) return;
  pollHandle = setInterval(refreshJobs, 1500);
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const files = Array.from(fileInput.files);
  if (files.length === 0) return;

  uploadStatus.textContent = `Encolando ${files.length} archivo(s)...`;
  uploadStatus.classList.remove("error");

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  try {
    const res = await fetch("/api/documents/uploads", { method: "POST", body: formData });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const jobs = await res.json();
    uploadStatus.textContent = `${jobs.length} archivo(s) en cola de indexacion.`;
    uploadForm.reset();
    await refreshJobs();
  } catch (err) {
    uploadStatus.textContent = `No se pudo subir los archivos: ${err.message}`;
    uploadStatus.classList.add("error");
  }
});

async function loadSummaries() {
  summaryStatus.textContent = "Cargando...";
  summaryStatus.classList.remove("error");
  try {
    const res = await fetch("/api/summaries");
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const summaries = await res.json();
    renderSummaries(summaries);
    summaryStatus.textContent = "";
  } catch (err) {
    summaryStatus.textContent = `No se pudo cargar la lista: ${err.message}`;
    summaryStatus.classList.add("error");
  }
}

function renderSummaries(summaries) {
  summaryCount.textContent = summaries.length;
  summaryTableBody.innerHTML = "";

  for (const summary of summaries) {
    const row = document.createElement("tr");

    const patientCell = document.createElement("td");
    patientCell.textContent = summary.nombre_paciente || summary.paciente_id || "—";

    const procCell = document.createElement("td");
    procCell.textContent = summary.procedimiento || "—";

    const classCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge badge-${summary.clasificacion}`;
    badge.textContent = CLASIFICACION_LABELS[summary.clasificacion] || summary.clasificacion;
    classCell.appendChild(badge);

    const detailCell = document.createElement("td");
    detailCell.className = "summary-detail";
    const parts = [];
    if (summary.sintomas_reportados) parts.push(`Síntomas: ${summary.sintomas_reportados}`);
    if (summary.siguientes_pasos) parts.push(`Próximos pasos: ${summary.siguientes_pasos}`);
    detailCell.textContent = parts.join("\n") || "—";

    const dateCell = document.createElement("td");
    dateCell.textContent = new Date(summary.creado_ts).toLocaleString();

    row.appendChild(patientCell);
    row.appendChild(procCell);
    row.appendChild(classCell);
    row.appendChild(detailCell);
    row.appendChild(dateCell);
    summaryTableBody.appendChild(row);
  }
}

refreshSummariesBtn.addEventListener("click", loadSummaries);
loadSummaries();

refreshBtn.addEventListener("click", loadDocuments);
closeDetailBtn.addEventListener("click", () => overlay.classList.add("hidden"));
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) overlay.classList.add("hidden");
});

loadDocuments();
refreshJobs();

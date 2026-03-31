const form = document.getElementById("resume-form");
const statusCard = document.getElementById("status-card");
const statusMessage = document.getElementById("status-message");
const errorDetails = document.getElementById("error-details");
const previewFrame = document.getElementById("preview-frame");
const downloadLink = document.getElementById("download-link");
const submitBtn = document.getElementById("submit-btn");

let currentObjectUrl = null;

function showStatus(message, isError = false) {
  statusCard.hidden = false;
  statusMessage.textContent = message;
  if (isError) {
    errorDetails.hidden = false;
  } else {
    errorDetails.hidden = true;
    errorDetails.textContent = "";
  }
}

function showError(message, details = "") {
  showStatus(message, true);
  errorDetails.textContent = details;
  previewFrame.hidden = true;
  downloadLink.hidden = true;
}

function resetPreview() {
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
  previewFrame.hidden = true;
  previewFrame.src = "about:blank";
  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
}

form.addEventListener("reset", () => {
  statusCard.hidden = true;
  statusMessage.textContent = "";
  errorDetails.hidden = true;
  errorDetails.textContent = "";
  resetPreview();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const referenceFile = form.reference.files[0];
  const profileFile = form.profile.files[0];
  const jobFile = form.job_description.files[0];
  const jobText = form.job_text.value.trim();

  if (!referenceFile || !profileFile) {
    showError("Reference resume and profile files are required.");
    return;
  }

  if (!jobFile && jobText.length === 0) {
    showError("Provide a job description as text or upload a .txt file.");
    return;
  }

  const formData = new FormData();
  formData.append("reference", referenceFile);
  formData.append("profile", profileFile);
  if (jobFile) {
    formData.append("job_description", jobFile);
  }
  if (jobText.length > 0) {
    formData.append("job_text", jobText);
  }

  resetPreview();
  submitBtn.disabled = true;
  submitBtn.textContent = "Generating…";
  showStatus("Processing your resume. This might take a few seconds.");

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const message = await response.text();
      showError("Resume generation failed.", message);
      return;
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    currentObjectUrl = objectUrl;

    previewFrame.hidden = false;
    previewFrame.src = objectUrl;

    downloadLink.hidden = false;
    downloadLink.href = objectUrl;

    showStatus("Resume generated successfully. Preview or download the PDF.");
  } catch (error) {
    showError("Unexpected error while reaching the API.", error.message ?? "Unknown error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Generate Resume";
  }
});

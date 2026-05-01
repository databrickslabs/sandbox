import { useState, useRef } from "react";
import { EvidenceItem } from "../types";

interface Props {
  index: number;
  item: EvidenceItem;
  onChange: (updated: EvidenceItem) => void;
  onRemove: () => void;
  canRemove: boolean;
}

export default function EvidenceField({ index, item, onChange, onRemove, canRemove }: Props) {
  const [locked, setLocked] = useState(false);
  const [csvWarning, setCsvWarning] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function detectType(file: File): "image" | "csv" | "text" {
    if (file.type.startsWith("image/")) return "image";
    if (file.type === "text/csv" || file.name.endsWith(".csv")) return "csv";
    return "text";
  }

  function processFile(file: File) {
    if (file.size > 5 * 1024 * 1024) {
      alert("File must be under 5MB");
      return;
    }
    const type = detectType(file);
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      onChange({ ...item, type, content: result, filename: file.name });
      if (type === "csv") {
        const rows = result.trim().split("\n").length;
        setCsvWarning(rows > 10);
      } else {
        setCsvWarning(false);
      }
    };
    if (type === "csv" || type === "text") {
      reader.readAsText(file);
    } else {
      reader.readAsDataURL(file);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
  }

  function handleAdd() {
    if (!item.content.trim()) return;
    setLocked(true);
  }

  function handleEdit() {
    setLocked(false);
  }

  const hasContent = item.content.trim().length > 0;

  const dropZoneStyle: React.CSSProperties = {
    border: `2px dashed ${dragging ? "#d4a853" : "#4a3f35"}`,
    borderRadius: 6,
    padding: "20px 12px",
    textAlign: "center",
    cursor: "pointer",
    background: dragging ? "rgba(212, 168, 83, 0.08)" : "transparent",
    transition: "border-color 0.2s, background 0.2s",
  };

  return (
    <div className="evidence-field" style={locked ? { borderColor: "#5a4a35", opacity: 0.85 } : {}}>
      <div className="evidence-header">
        <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>
          Clue {index + 1}
          {index >= 5 && <span className="text-muted"> (not scored)</span>}
          {locked && <span style={{ color: "#6abf7b", marginLeft: 8, fontSize: "0.8rem" }}>Added to case</span>}
        </span>
        <div className="flex-row">
          {canRemove && (
            <button type="button" className="btn-secondary btn-small" onClick={onRemove}>
              Remove
            </button>
          )}
        </div>
      </div>

      {locked ? (
        <div className="flex-row" style={{ justifyContent: "space-between" }}>
          <span className="text-muted" style={{ fontSize: "0.85rem", fontStyle: "italic" }}>
            {item.type === "text"
              ? item.content.length > 80 ? item.content.slice(0, 80) + "..." : item.content
              : item.type === "csv"
              ? "CSV data attached"
              : "Image attached"}
          </span>
          <button type="button" className="btn-secondary btn-small" onClick={handleEdit}>
            Edit
          </button>
        </div>
      ) : (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.csv,text/csv"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />

          {item.type === "text" && !item.content.startsWith("data:") ? (
            <div>
              <textarea
                placeholder="Type your findings, or drag & drop an image/CSV..."
                value={item.content}
                onChange={(e) => onChange({ ...item, content: e.target.value })}
                rows={2}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                style={dragging ? { borderColor: "#d4a853", background: "rgba(212, 168, 83, 0.08)" } : {}}
              />
              <button
                type="button"
                className="btn-secondary btn-small mt-8"
                onClick={() => fileInputRef.current?.click()}
                style={{ fontSize: "0.8rem" }}
              >
                Attach File
              </button>
            </div>
          ) : item.type === "image" ? (
            <div
              style={{ ...dropZoneStyle, padding: item.content ? 8 : "20px 12px" }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
            >
              {item.content ? (
                <>
                  <img
                    src={item.content}
                    alt="Evidence preview"
                    style={{ maxWidth: "100%", maxHeight: 200, borderRadius: 4 }}
                  />
                  <p className="text-muted" style={{ fontSize: "0.8rem", marginTop: 6 }}>
                    Drop a new image to replace
                  </p>
                </>
              ) : (
                <p style={{ color: dragging ? "#d4a853" : "#8a7e6a", fontSize: "0.9rem", margin: 0 }}>
                  {dragging ? "Drop it here..." : "Drag & drop an image here, or click to browse"}
                </p>
              )}
            </div>
          ) : (
            <div>
              <div
                style={{ ...dropZoneStyle, padding: 0, textAlign: "left", cursor: "pointer" }}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
              >
                <pre style={{
                  margin: 0,
                  padding: 8,
                  background: "transparent",
                  fontSize: "0.8rem",
                  maxHeight: 150,
                  overflow: "auto",
                  color: "#c4b89a",
                }}>
                  {item.content.slice(0, 500)}{item.content.length > 500 ? "..." : ""}
                </pre>
              </div>
              {csvWarning && (
                <p style={{ color: "#d4a853", fontSize: "0.85rem", marginTop: 8, fontStyle: "italic" }}>
                  Detectives need clues — make sure your uploads tell a story.
                </p>
              )}
            </div>
          )}

          {hasContent && (
            <button
              type="button"
              className="btn-primary btn-small mt-8"
              onClick={handleAdd}
            >
              Add to Case
            </button>
          )}
        </>
      )}
    </div>
  );
}

import { useDropzone } from 'react-dropzone'
import { Download, FileCode2 } from 'lucide-react'
import { downloadRubricTemplate } from '../lib/api'

interface Props {
  value: string
  onParsed: (yaml: string) => void
}

export function RubricUpload({ value, onParsed }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: 1,
    accept: {
      'application/x-yaml': ['.yaml', '.yml'],
      'text/yaml': ['.yaml', '.yml'],
      'text/plain': ['.yaml', '.yml'],
    },
    onDropAccepted: async (files) => {
      const txt = await files[0].text()
      onParsed(txt)
    },
  })

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-heading text-sm font-semibold">
          <FileCode2 className="h-4 w-4 text-link" /> Rubric YAML
        </h3>
        <button
          type="button"
          onClick={downloadRubricTemplate}
          className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs hover:bg-panel-muted"
        >
          <Download className="h-3.5 w-3.5" /> Template
        </button>
      </div>

      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border border-dashed p-3 text-sm ${
          isDragActive ? 'border-link bg-panel' : 'border-border bg-panel-muted'
        }`}
      >
        <input {...getInputProps()} />
        Upload or drop rubric YAML
      </div>

      <p className="mt-2 truncate text-xs text-fg-muted">{value ? 'Rubric loaded' : 'No rubric loaded'}</p>
    </section>
  )
}

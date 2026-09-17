import { useEffect, useState, type FormEvent } from "react";
import { apiFetch, clearAdminToken, getAdminToken, setAdminToken } from "../lib/api";

type ModelRow = {
  id: string;
  name: string;
  openRoutermodelName: string;
  accountIndex: string;
  testnetAccountIndex: string;
  invocationCount: number;
  hasMainnetCredentials: boolean;
  hasTestnetCredentials: boolean;
};

type FormState = {
  name: string;
  openRoutermodelName: string;
  lighterApiKey: string;
  accountIndex: string;
  testnetLighterApiKey: string;
  testnetAccountIndex: string;
};

const EMPTY_FORM: FormState = {
  name: "",
  openRoutermodelName: "",
  lighterApiKey: "",
  accountIndex: "",
  testnetLighterApiKey: "",
  testnetAccountIndex: "",
};

function CredentialBadge({ configured, label }: { configured: boolean; label: string }) {
  return (
    <span
      className={`inline-block font-mono text-[10px] px-2 py-0.5 border ${
        configured
          ? "border-emerald-600 text-emerald-700 dark:text-emerald-400"
          : "border-gray-400 text-gray-500 dark:text-gray-400"
      }`}
    >
      {label}: {configured ? "SET" : "MISSING"}
    </span>
  );
}

export default function ModelsManager() {
  const [models, setModels] = useState<ModelRow[] | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [unlocked, setUnlocked] = useState(() => Boolean(getAdminToken()));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function loadModels() {
    try {
      const response = await apiFetch("/models");
      if (!response.ok) {
        throw new Error("Failed to load models");
      }
      const payload = await response.json();
      setModels(payload.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models");
    }
  }

  useEffect(() => {
    void loadModels();
  }, []);

  function startEdit(model: ModelRow) {
    setEditingId(model.id);
    setForm({
      name: model.name,
      openRoutermodelName: model.openRoutermodelName,
      lighterApiKey: "",
      accountIndex: model.accountIndex,
      testnetLighterApiKey: "",
      testnetAccountIndex: model.testnetAccountIndex,
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleWrite(path: string, method: string, body?: unknown): Promise<boolean> {
    const response = await apiFetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (response.status === 401) {
      clearAdminToken();
      setUnlocked(false);
      setError("Admin token rejected. Unlock again to continue.");
      return false;
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `Request failed (${response.status})`);
    }
    return true;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (editingId) {
        const body: Record<string, string> = {
          name: form.name,
          openRoutermodelName: form.openRoutermodelName,
        };
        if (form.accountIndex.trim()) {
          body.accountIndex = form.accountIndex.trim();
        }
        if (form.testnetAccountIndex.trim()) {
          body.testnetAccountIndex = form.testnetAccountIndex.trim();
        }
        if (form.lighterApiKey.trim()) {
          body.lighterApiKey = form.lighterApiKey.trim();
        }
        if (form.testnetLighterApiKey.trim()) {
          body.testnetLighterApiKey = form.testnetLighterApiKey.trim();
        }
        const ok = await handleWrite(`/models/${editingId}`, "PATCH", body);
        if (!ok) {
          return;
        }
      } else {
        const ok = await handleWrite("/models", "POST", {
          name: form.name,
          openRoutermodelName: form.openRoutermodelName,
          lighterApiKey: form.lighterApiKey,
          accountIndex: form.accountIndex,
          testnetLighterApiKey: form.testnetLighterApiKey || null,
          testnetAccountIndex: form.testnetAccountIndex || null,
        });
        if (!ok) {
          return;
        }
      }
      resetForm();
      await loadModels();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(modelId: string) {
    if (!window.confirm("Delete this model? This fails if it already has history.")) {
      return;
    }
    setError(null);
    try {
      const ok = await handleWrite(`/models/${modelId}`, "DELETE");
      if (!ok) {
        return;
      }
      if (editingId === modelId) {
        resetForm();
      }
      await loadModels();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function handleUnlock(event: FormEvent) {
    event.preventDefault();
    const token = tokenInput.trim();
    if (!token) {
      setError("Enter the admin token.");
      return;
    }
    setAdminToken(token);
    setUnlocked(true);
    setTokenInput("");
    setError(null);
  }

  return (
    <div className="w-full h-full overflow-auto p-4 md:p-8">
      <h2 className="text-sm font-bold text-black dark:text-white font-mono mb-1">MODELS</h2>
      <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mb-4">
        API keys are write-only. After save they are never shown again.
      </p>

      {!unlocked && (
        <form onSubmit={handleUnlock} className="mb-6 max-w-md border-2 border-black dark:border-white p-3">
          <label className="block font-mono text-xs text-gray-900 dark:text-gray-100 mb-2">
            Unlock writes with admin token
            <input
              type="password"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              className="mt-1 w-full border-2 border-black dark:border-white bg-transparent px-2 py-1 font-mono text-xs"
            />
          </label>
          <button
            type="submit"
            className="font-mono text-xs px-3 py-1 bg-black text-white dark:bg-white dark:text-black border-2 border-black dark:border-white"
          >
            UNLOCK
          </button>
        </form>
      )}

      {error && (
        <p className="mb-4 font-mono text-xs text-red-600 dark:text-red-400">{error}</p>
      )}

      <form onSubmit={handleSubmit} className="mb-8 grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl">
        <Field
          label="Name"
          value={form.name}
          onChange={(value) => setForm((current) => ({ ...current, name: value }))}
          required
        />
        <Field
          label="OpenRouter model"
          value={form.openRoutermodelName}
          onChange={(value) => setForm((current) => ({ ...current, openRoutermodelName: value }))}
          required
        />
        <Field
          label={editingId ? "Mainnet API key (leave blank to keep)" : "Mainnet API key"}
          value={form.lighterApiKey}
          onChange={(value) => setForm((current) => ({ ...current, lighterApiKey: value }))}
          type="password"
        />
        <Field
          label="Mainnet account index"
          value={form.accountIndex}
          onChange={(value) => setForm((current) => ({ ...current, accountIndex: value }))}
        />
        <Field
          label={editingId ? "Testnet API key (leave blank to keep)" : "Testnet API key"}
          value={form.testnetLighterApiKey}
          onChange={(value) => setForm((current) => ({ ...current, testnetLighterApiKey: value }))}
          type="password"
        />
        <Field
          label="Testnet account index"
          value={form.testnetAccountIndex}
          onChange={(value) => setForm((current) => ({ ...current, testnetAccountIndex: value }))}
        />
        <div className="md:col-span-2 flex gap-2">
          <button
            type="submit"
            disabled={saving || !unlocked}
            className="font-mono text-xs px-3 py-1 bg-black text-white dark:bg-white dark:text-black border-2 border-black dark:border-white disabled:opacity-50"
          >
            {editingId ? "SAVE CHANGES" : "ADD MODEL"}
          </button>
          {editingId && (
            <button
              type="button"
              onClick={resetForm}
              className="font-mono text-xs px-3 py-1 border-2 border-black dark:border-white"
            >
              CANCEL
            </button>
          )}
        </div>
      </form>

      {!models ? (
        <p className="font-mono text-sm text-gray-500 dark:text-gray-400 animate-pulse">Loading models...</p>
      ) : models.length === 0 ? (
        <p className="font-mono text-sm text-gray-500 dark:text-gray-400">No models configured yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-2 border-black dark:border-white font-mono text-sm">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="text-left p-2 border-b-2 border-black dark:border-white">NAME</th>
                <th className="text-left p-2 border-b-2 border-black dark:border-white">OPENROUTER</th>
                <th className="text-left p-2 border-b-2 border-black dark:border-white">CREDENTIALS</th>
                <th className="text-right p-2 border-b-2 border-black dark:border-white">RUNS</th>
                <th className="text-right p-2 border-b-2 border-black dark:border-white">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={model.id} className="border-b border-gray-200 dark:border-gray-700">
                  <td className="p-2 text-gray-900 dark:text-gray-100">{model.name}</td>
                  <td className="p-2 text-gray-700 dark:text-gray-300">{model.openRoutermodelName}</td>
                  <td className="p-2 space-x-2">
                    <CredentialBadge configured={model.hasMainnetCredentials} label="LIVE" />
                    <CredentialBadge configured={model.hasTestnetCredentials} label="TESTNET" />
                  </td>
                  <td className="p-2 text-right">{model.invocationCount}</td>
                  <td className="p-2 text-right space-x-3">
                    <button
                      type="button"
                      disabled={!unlocked}
                      onClick={() => startEdit(model)}
                      className="underline disabled:opacity-50"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={!unlocked}
                      onClick={() => void handleDelete(model.id)}
                      className="underline text-red-600 dark:text-red-400 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="block font-mono text-xs text-gray-900 dark:text-gray-100">
      {label}
      <input
        type={type}
        required={required}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full border-2 border-black dark:border-white bg-transparent px-2 py-1 font-mono text-xs text-gray-900 dark:text-gray-100"
      />
    </label>
  );
}

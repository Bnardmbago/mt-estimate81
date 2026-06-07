"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";

type User = {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  preferred_locale: string;
  created_at: string;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export default function UserManager() {
  const t = useTranslations("admin.users");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [resettingId, setResettingId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [form, setForm] = useState({
    email: "",
    password: "",
    display_name: "",
    preferred_locale: "ja",
    is_admin: false,
  });

  const loadUsers = useCallback(async () => {
    setError(null);
    try {
      const data = await apiJson<User[]>("/admin/users");
      setUsers(data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t("loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setError(null);

    try {
      await apiJson<User>("/admin/users", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setForm({
        email: "",
        password: "",
        display_name: "",
        preferred_locale: "ja",
        is_admin: false,
      });
      await loadUsers();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : t("createError"));
    } finally {
      setCreating(false);
    }
  }

  async function toggleAdmin(user: User) {
    setError(null);
    try {
      await apiJson<User>(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_admin: !user.is_admin }),
      });
      await loadUsers();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : t("updateError"));
    }
  }

  async function updateLocale(user: User, preferred_locale: string) {
    setError(null);
    try {
      await apiJson<User>(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ preferred_locale }),
      });
      await loadUsers();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : t("updateError"));
    }
  }

  async function handleResetPassword(userId: string) {
    if (!newPassword) return;
    setError(null);
    try {
      await apiJson<User>(`/admin/users/${userId}/reset-password`, {
        method: "PUT",
        body: JSON.stringify({ password: newPassword }),
      });
      setResettingId(null);
      setNewPassword("");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : t("resetError"));
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">{t("loading")}</p>;
  }

  return (
    <div className="space-y-8">
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold">{t("createTitle")}</h2>
        <form onSubmit={(event) => void handleCreate(event)} className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("email")}</span>
            <input
              type="email"
              required
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("displayName")}</span>
            <input
              type="text"
              required
              value={form.display_name}
              onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("password")}</span>
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("locale")}</span>
            <select
              value={form.preferred_locale}
              onChange={(event) => setForm({ ...form, preferred_locale: event.target.value })}
              className={inputClassName}
            >
              <option value="ja">{t("localeJa")}</option>
              <option value="en">{t("localeEn")}</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(event) => setForm({ ...form, is_admin: event.target.checked })}
              className="rounded border-gray-300"
            />
            <span className="font-medium text-gray-700">{t("isAdmin")}</span>
          </label>
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={creating}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? t("creating") : t("create")}
            </button>
          </div>
        </form>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">{t("listTitle")}</h2>
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("email")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("displayName")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("locale")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("isAdmin")}</th>
                <th className="px-3 py-2 text-left font-medium text-gray-700">{t("actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-3 py-2">{user.email}</td>
                  <td className="px-3 py-2">{user.display_name}</td>
                  <td className="px-3 py-2">
                    <select
                      value={user.preferred_locale}
                      onChange={(event) => void updateLocale(user, event.target.value)}
                      className="rounded border border-gray-300 px-2 py-1 text-sm"
                    >
                      <option value="ja">{t("localeJa")}</option>
                      <option value="en">{t("localeEn")}</option>
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => void toggleAdmin(user)}
                      className={`rounded px-2 py-1 text-xs font-medium ${
                        user.is_admin
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {user.is_admin ? t("adminYes") : t("adminNo")}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    {resettingId === user.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="password"
                          minLength={8}
                          placeholder={t("newPassword")}
                          value={newPassword}
                          onChange={(event) => setNewPassword(event.target.value)}
                          className="rounded border border-gray-300 px-2 py-1 text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => void handleResetPassword(user.id)}
                          className="text-blue-600 hover:underline"
                        >
                          {t("savePassword")}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setResettingId(null);
                            setNewPassword("");
                          }}
                          className="text-gray-500 hover:underline"
                        >
                          {t("cancel")}
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setResettingId(user.id)}
                        className="text-blue-600 hover:underline"
                      >
                        {t("resetPassword")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

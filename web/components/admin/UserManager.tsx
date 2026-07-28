"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import PasswordField from "@/components/PasswordField";
import { apiFetch, apiJson } from "@/lib/api";

type Currency = "JPY" | "USD" | "PHP";

type User = {
  id: string;
  email: string;
  display_name: string;
  company_name: string | null;
  account_type: "full" | "contact";
  is_admin: boolean;
  is_active: boolean;
  preferred_locale: string;
  preferred_currency: Currency;
  created_at: string;
};

type EditForm = {
  email: string;
  display_name: string;
  company_name: string;
  account_type: "full" | "contact";
  preferred_locale: string;
  preferred_currency: Currency;
  is_admin: boolean;
  is_active: boolean;
  password?: string;
};

const CURRENCIES: Currency[] = ["JPY", "USD", "PHP"];

const inputClassName =
  "w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

type UserTableProps = {
  users: User[];
  t: ReturnType<typeof useTranslations<"admin.users">>;
  showAdminColumn: boolean;
  showResetPassword: boolean;
  deletingId: string | null;
  resettingId: string | null;
  newPassword: string;
  onOpenEdit: (user: User) => void;
  onToggleActive: (user: User) => void;
  onUpdateLocale: (user: User, locale: string) => void;
  onUpdateCurrency: (user: User, currency: Currency) => void;
  onDelete: (user: User) => void;
  onStartResetPassword: (userId: string) => void;
  onResetPassword: (userId: string) => void;
  onCancelResetPassword: () => void;
  onNewPasswordChange: (password: string) => void;
};

function UserTable({
  users,
  t,
  showAdminColumn,
  showResetPassword,
  deletingId,
  resettingId,
  newPassword,
  onOpenEdit,
  onToggleActive,
  onUpdateLocale,
  onUpdateCurrency,
  onDelete,
  onStartResetPassword,
  onResetPassword,
  onCancelResetPassword,
  onNewPasswordChange,
}: UserTableProps) {
  if (users.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("email")}</th>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("displayName")}</th>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("companyName")}</th>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("locale")}</th>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("currency")}</th>
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("status")}</th>
            {showAdminColumn ? (
              <th className="px-3 py-2 text-left font-medium text-gray-700">{t("isAdmin")}</th>
            ) : null}
            <th className="px-3 py-2 text-left font-medium text-gray-700">{t("actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {users.map((user) => (
            <tr key={user.id} className={!user.is_active ? "bg-gray-50 opacity-70" : undefined}>
              <td className="px-3 py-2">{user.email}</td>
              <td className="px-3 py-2">{user.display_name}</td>
              <td className="px-3 py-2">{user.company_name ?? "—"}</td>
              <td className="px-3 py-2">
                <select
                  value={user.preferred_locale}
                  onChange={(event) => void onUpdateLocale(user, event.target.value)}
                  className="rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  <option value="ja">{t("localeJa")}</option>
                  <option value="en">{t("localeEn")}</option>
                </select>
              </td>
              <td className="px-3 py-2">
                <select
                  value={user.preferred_currency}
                  onChange={(event) =>
                    void onUpdateCurrency(user, event.target.value as Currency)
                  }
                  className="rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  {CURRENCIES.map((currency) => (
                    <option key={currency} value={currency}>
                      {t(`currency${currency}` as "currencyJPY")}
                    </option>
                  ))}
                </select>
              </td>
              <td className="px-3 py-2">
                <button
                  type="button"
                  onClick={() => void onToggleActive(user)}
                  className={`rounded px-2 py-1 text-xs font-medium ${
                    user.is_active
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {user.is_active ? t("activeYes") : t("activeNo")}
                </button>
              </td>
              {showAdminColumn ? (
                <td className="px-3 py-2">
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      user.is_admin
                        ? "bg-blue-100 text-blue-800"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {user.is_admin ? t("adminYes") : t("adminNo")}
                  </span>
                </td>
              ) : null}
              <td className="px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onOpenEdit(user)}
                    className="text-blue-600 hover:underline"
                  >
                    {t("edit")}
                  </button>
                  {showResetPassword ? (
                    <button
                      type="button"
                      onClick={() => onStartResetPassword(user.id)}
                      className="text-blue-600 hover:underline"
                    >
                      {t("resetPassword")}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => void onDelete(user)}
                    disabled={deletingId === user.id}
                    className="text-red-600 hover:underline disabled:opacity-50"
                  >
                    {deletingId === user.id ? t("deleting") : t("delete")}
                  </button>
                </div>
                {showResetPassword && resettingId === user.id && (
                  <div className="mt-2 flex items-center gap-2">
                    <PasswordField
                      minLength={8}
                      placeholder={t("newPassword")}
                      value={newPassword}
                      onChange={(event) => onNewPasswordChange(event.target.value)}
                      className="rounded border border-gray-300 px-2 py-1 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => void onResetPassword(user.id)}
                      className="text-blue-600 hover:underline"
                    >
                      {t("savePassword")}
                    </button>
                    <button
                      type="button"
                      onClick={onCancelResetPassword}
                      className="text-gray-500 hover:underline"
                    >
                      {t("cancel")}
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function UserManager() {
  const t = useTranslations("admin.users");
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [resettingId, setResettingId] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [upgradePassword, setUpgradePassword] = useState("");
  const [editForm, setEditForm] = useState<EditForm>({
    email: "",
    display_name: "",
    company_name: "",
    account_type: "full",
    preferred_locale: "ja",
    preferred_currency: "JPY",
    is_admin: false,
    is_active: true,
  });
  const [form, setForm] = useState({
    email: "",
    password: "",
    display_name: "",
    company_name: "",
    preferred_locale: "ja",
    preferred_currency: "JPY" as Currency,
    is_admin: false,
    is_active: true,
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

  function openEdit(user: User) {
    setEditingUser(user);
    setEditForm({
      email: user.email,
      display_name: user.display_name,
      company_name: user.company_name ?? "",
      account_type: user.account_type ?? "full",
      preferred_locale: user.preferred_locale,
      preferred_currency: user.preferred_currency,
      is_admin: user.is_admin,
      is_active: user.is_active,
    });
    setUpgradePassword("");
    setError(null);
  }

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
        company_name: "",
        preferred_locale: "ja",
        preferred_currency: "JPY",
        is_admin: false,
        is_active: true,
      });
      await loadUsers();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : t("createError"));
    } finally {
      setCreating(false);
    }
  }

  async function handleSaveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editingUser) return;

    setSavingEdit(true);
    setError(null);
    try {
      const payload: EditForm = { ...editForm };
      if (
        editingUser.account_type === "contact" &&
        editForm.account_type === "full" &&
        upgradePassword.trim()
      ) {
        payload.password = upgradePassword.trim();
      }
      await apiJson<User>(`/admin/users/${editingUser.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setEditingUser(null);
      await loadUsers();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : t("updateError"));
    } finally {
      setSavingEdit(false);
    }
  }

  async function toggleActive(user: User) {
    setError(null);
    try {
      await apiJson<User>(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      await loadUsers();
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : t("updateError"));
    }
  }

  async function handleDelete(user: User) {
    if (!window.confirm(t("deleteConfirm", { email: user.email }))) {
      return;
    }

    setDeletingId(user.id);
    setError(null);
    try {
      const response = await apiFetch(`/admin/users/${user.id}`, { method: "DELETE" });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(
          typeof payload.detail === "object" && payload.detail?.error
            ? payload.detail.error
            : t("deleteError"),
        );
      }
      await loadUsers();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : t("deleteError"));
    } finally {
      setDeletingId(null);
    }
  }

  async function updateCurrency(user: User, preferred_currency: Currency) {
    setError(null);
    try {
      await apiJson<User>(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ preferred_currency }),
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

  const fullUsers = users.filter((user) => user.account_type !== "contact");
  const contactUsers = users.filter((user) => user.account_type === "contact");

  const userTableProps = {
    t,
    deletingId,
    resettingId,
    newPassword,
    onOpenEdit: openEdit,
    onToggleActive: toggleActive,
    onUpdateLocale: updateLocale,
    onUpdateCurrency: updateCurrency,
    onDelete: handleDelete,
    onStartResetPassword: setResettingId,
    onResetPassword: handleResetPassword,
    onCancelResetPassword: () => {
      setResettingId(null);
      setNewPassword("");
    },
    onNewPasswordChange: setNewPassword,
  };

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
            <span className="mb-1 block font-medium text-gray-700">{t("companyName")}</span>
            <input
              type="text"
              value={form.company_name}
              onChange={(event) => setForm({ ...form, company_name: event.target.value })}
              placeholder={t("companyNamePlaceholder")}
              className={inputClassName}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("password")}</span>
            <PasswordField
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
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">{t("currency")}</span>
            <select
              value={form.preferred_currency}
              onChange={(event) =>
                setForm({ ...form, preferred_currency: event.target.value as Currency })
              }
              className={inputClassName}
            >
              {CURRENCIES.map((currency) => (
                <option key={currency} value={currency}>
                  {t(`currency${currency}` as "currencyJPY")}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(event) => setForm({ ...form, is_admin: event.target.checked })}
              className="rounded border-gray-300"
            />
            <span className="font-medium text-gray-700">{t("isAdmin")}</span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
              className="rounded border-gray-300"
            />
            <span className="font-medium text-gray-700">{t("isActive")}</span>
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

      {editingUser && (
        <section className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <h2 className="mb-4 text-lg font-semibold">{t("editTitle")}</h2>
          <form onSubmit={(event) => void handleSaveEdit(event)} className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("email")}</span>
              <input
                type="email"
                required
                value={editForm.email}
                onChange={(event) => setEditForm({ ...editForm, email: event.target.value })}
                className={inputClassName}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("displayName")}</span>
              <input
                type="text"
                required
                value={editForm.display_name}
                onChange={(event) =>
                  setEditForm({ ...editForm, display_name: event.target.value })
                }
                className={inputClassName}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("companyName")}</span>
              <input
                type="text"
                value={editForm.company_name}
                onChange={(event) =>
                  setEditForm({ ...editForm, company_name: event.target.value })
                }
                placeholder={t("companyNamePlaceholder")}
                className={inputClassName}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("locale")}</span>
              <select
                value={editForm.preferred_locale}
                onChange={(event) =>
                  setEditForm({ ...editForm, preferred_locale: event.target.value })
                }
                className={inputClassName}
              >
                <option value="ja">{t("localeJa")}</option>
                <option value="en">{t("localeEn")}</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-gray-700">{t("currency")}</span>
              <select
                value={editForm.preferred_currency}
                onChange={(event) =>
                  setEditForm({
                    ...editForm,
                    preferred_currency: event.target.value as Currency,
                  })
                }
                className={inputClassName}
              >
                {CURRENCIES.map((currency) => (
                  <option key={currency} value={currency}>
                    {t(`currency${currency}` as "currencyJPY")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm sm:col-span-2">
              <span className="mb-1 block font-medium text-gray-700">{t("accountType")}</span>
              <select
                value={editForm.account_type}
                onChange={(event) =>
                  setEditForm({
                    ...editForm,
                    account_type: event.target.value as "full" | "contact",
                  })
                }
                className={inputClassName}
              >
                <option value="full">{t("accountTypeFull")}</option>
                <option value="contact">{t("accountTypeContact")}</option>
              </select>
            </label>
            {editingUser?.account_type === "contact" && editForm.account_type === "full" ? (
              <label className="block text-sm sm:col-span-2">
                <span className="mb-1 block font-medium text-gray-700">{t("upgradePassword")}</span>
                <PasswordField
                  minLength={8}
                  required
                  value={upgradePassword}
                  onChange={(event) => setUpgradePassword(event.target.value)}
                  className={inputClassName}
                />
              </label>
            ) : null}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={editForm.is_admin}
                onChange={(event) => setEditForm({ ...editForm, is_admin: event.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="font-medium text-gray-700">{t("isAdmin")}</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(event) => setEditForm({ ...editForm, is_active: event.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="font-medium text-gray-700">{t("isActive")}</span>
            </label>
            <div className="flex gap-2 sm:col-span-2">
              <button
                type="submit"
                disabled={savingEdit}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {savingEdit ? t("saving") : t("save")}
              </button>
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {t("cancel")}
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="space-y-6">
        <div>
          <h2 className="mb-4 text-lg font-semibold">{t("listTitleFull")}</h2>
          {fullUsers.length === 0 ? (
            <p className="text-sm text-gray-500">{t("emptyFull")}</p>
          ) : (
            <UserTable
              {...userTableProps}
              users={fullUsers}
              showAdminColumn
              showResetPassword
            />
          )}
        </div>

        <div>
          <h2 className="mb-4 text-lg font-semibold">{t("listTitleContact")}</h2>
          {contactUsers.length === 0 ? (
            <p className="text-sm text-gray-500">{t("emptyContact")}</p>
          ) : (
            <UserTable
              {...userTableProps}
              users={contactUsers}
              showAdminColumn={false}
              showResetPassword={false}
            />
          )}
        </div>
      </section>
    </div>
  );
}

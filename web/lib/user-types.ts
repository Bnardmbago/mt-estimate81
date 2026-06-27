export type AccountType = "full" | "contact";

export type UserProfile = {
  id: string;
  email: string;
  display_name: string;
  company_name: string | null;
  account_type: AccountType;
  email_verified_at: string | null;
  is_admin: boolean;
  is_active: boolean;
  preferred_locale: string;
  preferred_currency: string;
};

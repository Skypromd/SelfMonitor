import { ReactNode } from 'react';

export type PlatformUser = {
  email?: string;
  is_admin?: boolean;
};

/** Today: platform operators are JWT users with is_admin. Replace with role/permissions when RBAC lands. */
export function isPlatformOperator(user: PlatformUser): boolean {
  return user.is_admin === true;
}

type AdminGuardProps = {
  children: ReactNode;
  user: PlatformUser;
  /** Rendered when the user is not allowed (e.g. redirect handled by parent). */
  fallback?: ReactNode;
};

export default function AdminGuard({ children, user, fallback = null }: AdminGuardProps) {
  if (!isPlatformOperator(user)) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}

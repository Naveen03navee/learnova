import { Badge } from "@/components/ui/badge";
import { Globe, User, Users, Lock, Eye, Edit2 } from "lucide-react";

interface AccessBadgeProps {
  access: {
    level: "OWNER" | "EDIT" | "VIEW" | "NONE";
    is_global: boolean;
    is_shared: boolean;
  };
  className?: string;
}

export function AccessBadge({ access, className }: AccessBadgeProps) {
  if (!access) return null;

  if (access.is_global) {
    return (
      <Badge variant="outline" className={`bg-slate-50 text-slate-600 border-slate-200 gap-1 font-normal ${className}`}>
        <Globe className="h-3 w-3" />
        Global
      </Badge>
    );
  }

  if (access.level === "OWNER") {
    return (
      <Badge variant="outline" className={`bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-normal ${className}`}>
        <User className="h-3 w-3" />
        Owned by you
      </Badge>
    );
  }

  if (access.is_shared) {
    const isEdit = access.level === "EDIT";
    return (
      <Badge variant="outline" className={`gap-1 font-normal ${
        isEdit ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"
      } ${className}`}>
        <Users className="h-3 w-3" />
        Shared {isEdit ? "(Edit)" : "(View only)"}
      </Badge>
    );
  }

  // Fallback for no access (shouldn't really see this due to backend filtering)
  return (
    <Badge variant="outline" className={`bg-red-50 text-red-700 border-red-200 gap-1 font-normal ${className}`}>
      <Lock className="h-3 w-3" />
      No Access
    </Badge>
  );
}

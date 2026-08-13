"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import { Share2, Trash2, Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";

interface SharePermission {
  id: string;
  shared_with_email: string;
  permission_level: "VIEW" | "EDIT" | "OWNER";
}

interface ShareDialogProps {
  entityType: "exam" | "resource" | "pattern" | "question" | "paper";
  entityId: string;
  trigger?: React.ReactElement;
}

export function ShareDialog({ entityType, entityId, trigger }: ShareDialogProps) {
  const [open, setOpen] = useState(false);
  const [shares, setShares] = useState<SharePermission[]>([]);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [level, setLevel] = useState<"VIEW" | "EDIT">("VIEW");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchShares = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/v1/shares/${entityType}/${entityId}`);
      setShares(data);
    } catch (error: any) {
      toast.error("Failed to load sharing settings", {
        description: error.response?.data?.detail || error.message
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchShares();
    }
  }, [open, entityType, entityId]);

  const handleShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    try {
      await api.post("/api/v1/shares", {
        entity_type: entityType,
        entity_id: entityId,
        shared_with_email: email,
        permission_level: level
      });
      toast.success(`Shared with ${email}`);
      setEmail("");
      fetchShares();
    } catch (error: any) {
      toast.error("Failed to share", {
        description: error.response?.data?.detail || error.message
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevoke = async (shareId: string) => {
    try {
      await api.delete(`/api/v1/shares/${shareId}`);
      toast.success("Access revoked");
      setShares(shares.filter(s => s.id !== shareId));
    } catch (error: any) {
      toast.error("Failed to revoke access", {
        description: error.response?.data?.detail || error.message
      });
    }
  };

  const updateLevel = async (shareId: string, newLevel: "VIEW" | "EDIT") => {
    try {
      await api.put(`/api/v1/shares/${shareId}`, { permission_level: newLevel });
      toast.success("Permission updated");
      fetchShares();
    } catch (error: any) {
      toast.error("Failed to update permission", {
        description: error.response?.data?.detail || error.message
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger 
        render={
          trigger || (
            <Button variant="outline" size="sm" className="h-8 gap-1">
              <Share2 className="h-4 w-4" />
              <span>Share</span>
            </Button>
          )
        }
      />
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Share {entityType}</DialogTitle>
          <DialogDescription>
            Grant other teachers access to this {entityType}.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleShare} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 mt-4">
          <Input 
            placeholder="Teacher's email address" 
            type="email" 
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="flex-1"
            required
          />
          <Select value={level} onValueChange={(val: any) => setLevel(val)}>
            <SelectTrigger className="w-full sm:w-[110px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="VIEW">View</SelectItem>
              <SelectItem value="EDIT">Edit</SelectItem>
            </SelectContent>
          </Select>
          <Button type="submit" disabled={isSubmitting || !email}>
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Invite"}
          </Button>
        </form>

        <div className="mt-6 space-y-4">
          <h4 className="text-sm font-medium text-slate-900 flex items-center gap-2">
            <UserPlus className="h-4 w-4 text-slate-500" />
            People with access
          </h4>
          
          <div className="space-y-3 max-h-[240px] overflow-y-auto pr-2">
            {loading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
              </div>
            ) : shares.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-4">
                This {entityType} is not shared with anyone yet.
              </p>
            ) : (
              shares.map((share) => (
                <div key={share.id} className="flex items-center justify-between group rounded-md p-2 hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-700">{share.shared_with_email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Select 
                      value={share.permission_level} 
                      onValueChange={(val: any) => updateLevel(share.id, val)}
                    >
                      <SelectTrigger className="h-8 w-[90px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="VIEW">Viewer</SelectItem>
                        <SelectItem value="EDIT">Editor</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 text-slate-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRevoke(share.id)}
                      title="Remove access"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

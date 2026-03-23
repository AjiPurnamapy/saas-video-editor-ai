"use client";

import { LogOut, Menu, Plus } from "lucide-react";

import { useCurrentUser, useLogout } from "@/hooks/use-auth";
import { useUIStore } from "@/stores/ui-store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Topbar() {
  const { data: user } = useCurrentUser();
  const logout = useLogout();
  const { toggleSidebar, setUploadDialogOpen } = useUIStore();

  const initials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 backdrop-blur-sm lg:px-6">
      {/* Left: hamburger + title */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="text-slate-400 lg:hidden"
          onClick={toggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      {/* Right: upload + user menu */}
      <div className="flex items-center gap-3">
        <Button
          onClick={() => setUploadDialogOpen(true)}
          className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/20"
          size="sm"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          Upload Video
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger
            className="relative h-9 w-9 rounded-full"
          >
            <Avatar className="h-9 w-9 border border-slate-700">
              <AvatarFallback className="bg-slate-800 text-xs text-slate-300">
                {initials}
              </AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-56 border-slate-800 bg-slate-900"
          >
            <div className="px-2 py-1.5">
              <p className="text-sm font-medium text-white">{user?.email}</p>
              <p className="text-xs text-slate-500">
                {user?.is_email_verified ? "Verified" : "Unverified"}
              </p>
            </div>
            <DropdownMenuSeparator className="bg-slate-800" />
            <DropdownMenuItem
              onClick={() => logout.mutate()}
              className="text-red-400 focus:bg-red-500/10 focus:text-red-400 cursor-pointer"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

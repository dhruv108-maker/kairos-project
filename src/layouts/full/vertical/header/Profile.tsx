import { useNavigate } from "react-router";
import { Sheet, SheetTrigger, SheetContent, SheetFooter, SheetClose } from "src/components/ui/sheet";
import { Avatar, AvatarFallback } from "src/components/ui/avatar";
import { Button } from "src/components/ui/button";
import { Mailbox, X } from "lucide-react";
import { useAuth } from "@/context/auth/AuthContext";

const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("") || "K";

export default function ProfileSheet() {
  const { account, logout } = useAuth();
  const navigate = useNavigate();
  const name = account?.full_name ?? "Kairos user";

  const handleLogout = () => {
    logout();
    navigate("/auth/auth2/login", { replace: true });
  };

  return (
    <Sheet>
      <SheetTrigger className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-full hover:bg-primary/5" aria-label="Open account menu">
        <Avatar className="h-8 w-8">
          <AvatarFallback>{initials(name)}</AvatarFallback>
        </Avatar>
      </SheetTrigger>
      <SheetContent showCloseButton={false} side="right" className="w-full max-w-80 border-s-0">
        <SheetClose className="absolute right-5 top-5 rounded-full p-2 hover:bg-primary/5 hover:text-primary" aria-label="Close account menu">
          <X className="h-5 w-5" />
        </SheetClose>
        <div className="px-6 py-10">
          <div className="flex flex-col items-center justify-center gap-4">
            <Avatar className="h-16 w-16">
              <AvatarFallback className="text-lg">{initials(name)}</AvatarFallback>
            </Avatar>
            <div className="text-center">
              <h2 className="text-lg font-semibold">{name}</h2>
              <div className="mt-2 flex items-center justify-center gap-2 text-muted-foreground">
                <Mailbox size={16} />
                <span className="break-all text-sm">{account?.email ?? ""}</span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{account?.roles.join(" · ")}</p>
            </div>
          </div>
        </div>
        <SheetFooter className="border-t px-6 pt-6">
          <Button variant="outline" className="w-full" onClick={handleLogout}>Sign out</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

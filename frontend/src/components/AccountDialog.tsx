import { useState, type FormEvent } from "react";
import { api } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";
import { useAction } from "../hooks/useAsync";
import { Button, ErrorBanner, Field, Modal } from "./ui";

export function AccountDialog({ onClose }: { onClose: () => void }) {
  const { user, setUser, signOut } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const save = useAction(api.users.updateMe);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const updated = await save.run({ name: name.trim(), phone: phone.trim() || null });
    if (updated) {
      setUser(updated);
      onClose();
    }
  }

  return (
    <Modal title="Account" onClose={onClose}>
      <form onSubmit={submit} className="stack-sm">
        <Field label="Email" hint="Managed by your sign-in account.">
          <input value={user?.email ?? ""} disabled />
        </Field>
        <div className="grid-2">
          <Field label="Name" htmlFor="acc-name">
            <input id="acc-name" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Phone" htmlFor="acc-phone">
            <input id="acc-phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </Field>
        </div>
        <ErrorBanner error={save.error} />
        <div className="row-gap" style={{ justifyContent: "space-between" }}>
          <Button type="button" variant="ghost" className="text-danger" onClick={() => void signOut()}>
            Sign out
          </Button>
          <Button type="submit" variant="primary" loading={save.running}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  );
}

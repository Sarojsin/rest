import type { ReactNode } from "react";

type PageHeaderProps = {
  title: ReactNode;
  sub?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
};

export function PageHeader({ title, sub, actions, eyebrow }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <p className="kicker">{eyebrow}</p> : null}
        <h1 className="page-title">{title}</h1>
        {sub ? <p className="page-sub">{sub}</p> : null}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

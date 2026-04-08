import * as React from 'react';

export interface TabsProps {
  defaultValue?: string;
  children: React.ReactNode;
  className?: string;
}

export interface TabsListProps {
  children: React.ReactNode;
  className?: string;
}

export interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export const TabsContext = React.createContext<{
  activeValue: string;
  setActiveValue: (value: string) => void;
}>({ activeValue: '', setActiveValue: () => {} });

export const Tabs: React.FC<TabsProps> = ({ defaultValue = '', children, className }) => {
  const [activeValue, setActiveValue] = React.useState(defaultValue);
  return (
    <TabsContext.Provider value={{ activeValue, setActiveValue }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
};

export const TabsList: React.FC<TabsListProps> = ({ children, className }) => (
  <div className={`inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 ${className || ''}`}>
    {children}
  </div>
);

export const TabsTrigger: React.FC<TabsTriggerProps> = ({ value, children, className, onClick }) => {
  const { activeValue, setActiveValue } = React.useContext(TabsContext);
  const isActive = activeValue === value;
  return (
    <button
      onClick={() => { setActiveValue(value); onClick?.(); }}
      className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none ${isActive ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground'} ${className || ''}`}
    >
      {children}
    </button>
  );
};

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className }) => {
  const { activeValue } = React.useContext(TabsContext);
  if (activeValue !== value) return null;
  return <div className={`mt-2 ${className || ''}`}>{children}</div>;
};

import "./styles.css";

export const metadata = {
  title: "StudyLab",
  description: "Source-grounded AI study lab",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-start justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold tracking-tight">Hammer Ontology</h1>
      <p className="text-muted-foreground">
        디자인 데이터 온톨로지 관리 앱을 준비하고 있습니다.
      </p>
      <Button disabled>준비 중</Button>
    </main>
  );
}

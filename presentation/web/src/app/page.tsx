import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-start justify-center gap-4 px-6">
      <h1 className="text-3xl font-semibold tracking-tight">
        Hammer Presentation
      </h1>
      <p className="text-muted-foreground">
        AI 프레젠테이션 앱을 준비하고 있습니다.
      </p>
      <Button disabled>준비 중</Button>
    </main>
  );
}

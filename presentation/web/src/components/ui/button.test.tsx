import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { Button } from "@/components/ui/button";

test("disabled state prevents the primary action", () => {
  const onClick = vi.fn();
  const { rerender } = render(<Button onClick={onClick}>시작</Button>);

  fireEvent.click(screen.getByRole("button", { name: "시작" }));
  expect(onClick).toHaveBeenCalledTimes(1);

  rerender(
    <Button disabled onClick={onClick}>
      시작
    </Button>,
  );
  expect(screen.getByRole("button", { name: "시작" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "시작" }));
  expect(onClick).toHaveBeenCalledTimes(1);
});

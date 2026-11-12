import { test, expect } from "@playwright/test";

test("landing explica o produto sem depender de headline decorativo", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading",{level:1,name:"Converse com seus amigos em tempo real."})).toBeVisible();
  await expect(page.getByRole("link",{name:"Criar conta"}).first()).toBeVisible();
  await expect(page.locator(".preview-disclaimer")).toContainText("Prévia ilustrativa");
  await expect(page.locator(".hero-copy h1 em")).toHaveCount(0);
});

test("login e cadastro têm formulários operáveis", async ({ page }) => {
  await page.goto("/app.html?mode=login");
  await expect(page.getByRole("heading",{name:"Entre no FriendsMeeting."})).toBeVisible();
  await expect(page.locator("#email")).toBeVisible();
  await page.getByRole("button",{name:"Criar conta"}).click();
  await expect(page.locator("#username")).toBeVisible();
  await expect(page.locator("#password")).toHaveAttribute("autocomplete","new-password");
});

test("demonstração permite conversar sem perder foco após envio", async ({ page }) => {
  await page.goto("/app.html?demo=1");
  const input = page.getByRole("textbox",{name:"Escrever mensagem"});
  await expect(input).toBeVisible();
  await input.fill("Mensagem de teste do navegador");
  await input.press("Enter");
  await expect(page.locator(".message-bubble",{hasText:"Mensagem de teste do navegador"})).toHaveCount(1);
  await expect(input).toBeFocused();
  await expect(input).toHaveValue("");
});

test("preferências alteram tema e perfil continua acessível", async ({ page }) => {
  await page.goto("/app.html?demo=1");
  await page.getByRole("button",{name:"Configurações"}).click();
  await page.getByRole("button",{name:"Claro"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme","light");
  await page.getByRole("button",{name:"Escuro"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme","dark");
  await page.getByRole("button",{name:"Meu perfil"}).first().click();
  await expect(page.getByRole("heading",{name:"Meu perfil"})).toBeVisible();
});


test("atualizar conversas preserva o rascunho, cursor e foco", async ({ page }) => {
  await page.goto("/app.html?demo=1");
  const input=page.getByRole("textbox",{name:"Escrever mensagem"});
  await input.fill("Rascunho ainda não enviado");
  await input.evaluate(el=>el.setSelectionRange(5,5));
  // O acionamento programático isola o rerender: um clique humano move o foco ao botão.\n  await page.locator('[aria-label="Atualizar conversas"]').evaluate(button=>button.click());
  await expect(input).toHaveValue("Rascunho ainda não enviado");
  await expect(input).toBeFocused();
  const selection=await input.evaluate(el=>[el.selectionStart,el.selectionEnd]);
  expect(selection).toEqual([5,5]);
});

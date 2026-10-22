"""404 page. Every URL in it is absolute (base-prefixed), so it works at any depth."""
from .core import circle, e, icon
from .layout import page


def render(ctx):
    body = f"""
<section class="notfound" aria-labelledby="notfound-title">
  <p class="notfound__roll"><span>{ctx.t("notfound.roll")}</span>{circle(ctx.t("notfound.absent"))}</p>
  <h1 id="notfound-title">{ctx.t("notfound.title")}</h1>
  <p>{ctx.t("notfound.body")}</p>
  <div class="notfound__actions">
    <a class="btn btn--primary" href="{e(ctx.url())}"><span>{ctx.t("notfound.home")}</span>{icon("arrow")}</a>
    <a class="btn btn--ghost" href="{e(ctx.url("demo/"))}">{ctx.t("notfound.demo")}</a>
  </div>
</section>"""
    return page(
        ctx,
        title=ctx.t("meta.notfound_title"),
        description=ctx.t("notfound.body"),
        body=body,
        noindex=True,
    )

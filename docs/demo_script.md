# Demo script

Spoken script for walking through `docs/deck/`. The lines in **English** are what
you say. The notes in **中文** are delivery: pacing, emphasis, and why each move
is there.

Three versions: 30 seconds, 2 minutes, and the full ~13-minute walkthrough.
Q&A prep at the end.

---

## The three things they should remember

Everything below is in service of these. If someone remembers nothing else,
these three are the ones worth landing:

1. **I know where it is legitimate to simulate and where it is not.**
   Surrogate for the systems question, published data for the physics question.
2. **I built governance that can actually refuse, and I can price what it costs.**
   `blocked` is not `failed`; the benchmark reports both.
3. **I found five defects in my own build, four of them silent.**
   That is the judgment signal. Anyone can show what worked.

> 中文：这三条是整场的锚。每一张幻灯片都在为其中一条服务。讲之前先在心里确认——
> 如果对方只记住三句话，是不是这三句。**不要试图让他们记住十六张幻灯片。**

---

## 30 seconds — the elevator version

> I built a prototype of the layer between an AI's next-experiment suggestion and
> the evidence that it actually ran. Two use cases: a closed-loop process
> optimization on a surrogate I'm honest about being a surrogate, and a candidate
> triage built on published superconductor data with no simulated physics at all.
> The interesting part isn't the optimizer — it's the governance. The safety gate
> can refuse to spend a sample, and the benchmark reports what that refusal costs.

> 中文：**"the interesting part isn't the optimizer"** 这句是钩子。大多数人以为
> AI-for-science 的重点是模型；你把重点放在治理上，立刻区分开了。
> 30 秒版用于：走廊偶遇、自我介绍轮、对方说"简单说说"。

---

## 2 minutes — when they say "give me the short version"

> Materials models propose candidates far faster than labs can evaluate them. The
> bottleneck isn't model accuracy — it's that a prediction doesn't automatically
> become an experiment, and an experiment doesn't automatically become
> trustworthy data. That gap is operational, and that's what I built.
>
> Two use cases, chosen to sit on opposite sides of a line. For CdTe thin films I
> use a noisy surrogate — deliberately hard, with a non-smooth process window, an
> over-treatment cliff, and outright failures — because the question there is
> about systems, not physics. For hydride superconductors I simulate nothing at
> all. I transcribed the published tables from a 2026 Communications Physics paper
> and built triage on top of them.
>
> The part I'd want to talk about is the safety gate. It doesn't just annotate
> risky parameters — it refuses to run them, before any device is touched. So I
> report `blocked` separately from `failed`, because a failure burned a sample and
> a block prevented one from being burned. Those cost a real lab completely
> different amounts. And the guardrail sits deliberately wider than the true
> failure region, which costs the optimizer reachable search space. Governance
> isn't free, and I'd rather the system show its price than hide it.
>
> I can go deeper wherever is useful — the benchmark, the triage, or the five
> defects I found in my own build.

> 中文：结尾那句**把选择权交给对方**，比你自己决定讲哪部分好。
> 很多面试官会直接选"the five defects"——那正是你最想讲的那张。

---

## Full walkthrough — ~13 minutes

Timings are targets, not a script to race through. Say up front that you welcome
interruptions; a walkthrough that gets interrupted is going well.

> **Opening line, before slide 1:**
> "This is about fifteen minutes. Please interrupt whenever — I'd rather have the
> conversation than the presentation."

> 中文：这句开场是有用的。它把"演示"变成"对话"，而且如果对方真的打断了，你
> 不会慌——你已经预告过了。

---

### 1 · Title — 20s

> I've called this an AI-to-Lab Orchestrator. It's the operating layer between an
> AI's next-experiment suggestion and the evidence that it actually ran.
>
> One thing up front, because it's the boundary I most want to be trusted on:
> this is not a physics simulator, and it never claims to be.

> 中文：**开场就说"这不是物理模拟器"**。主动划边界 = 你知道边界在哪。
> 如果等到对方问，同样的话就变成防守。不要停在这张，20 秒内走。

---

### 2 · Predictions outpace validation — 60s

> The framing I started from: models propose candidates far faster than labs can
> evaluate them. And the bottleneck isn't model accuracy. It's that a prediction
> doesn't automatically become an experiment, an experiment doesn't automatically
> become trustworthy data, and trustworthy data doesn't automatically become the
> next decision.
>
> Everything in that gap is operational. What do we try next, and by whose
> definition of a good result. Is it safe to run. Did it actually run. Is the data
> clean enough to feed back into a model. What did we learn.
>
> None of that is a modelling problem. All of it decides how fast the loop turns —
> and the speed of that loop is the ceiling on how fast an AI-for-science
> programme can iterate.

> 中文：最后一句是**把技术连到项目管理**的桥。你不是在说"我会写代码"，你是在说
> "我知道什么决定了研究吞吐量"。这是 PM 岗位真正关心的。
> 语速放慢在 "None of that is a modelling problem"。

---

### 3 · Five layers — 45s

> The system is five layers, and I'd organise them by the question each answers,
> because in a real lab those questions have different owners. Instruments,
> scheduling, data, research strategy, and safety are not one person's job.
>
> Three are done, two are partial — the status column is honest.

> 中文：这张**快速过**。它是地图，不是内容。
> 「status 列是诚实的」这半句值得说——大部分 portfolio 的架构图都假装一切完成。

---

### 4 · Scientific honesty over fake physics — 90s ★

> This is the slide I'd lead with if I only had one.
>
> The principle is: where physical fidelity matters, use published data. Where
> systems benchmarking matters, use a transparent surrogate that's honest about
> being one. And I picked the two use cases to sit on opposite sides of that line.
>
> CdTe is the surrogate side. It's a benchmark environment — deliberately hard,
> with observation noise, a narrow non-smooth treatment window, an over-treatment
> cliff, parameter interactions, and experiments that just fail. What it is not is
> a physically accurate CdTe simulator, and I make no claim about real device
> efficiency.
>
> Hydrides are the published-data side. I simulate nothing — no DFPT, no
> electron-phonon coupling, no Tc. I transcribed twenty-two candidates verbatim
> from the published tables and built triage on top.
>
> The reason this matters more than any individual feature: knowing which of those
> two modes a problem calls for is the judgment the work actually needs. Getting
> it wrong in the other direction — faking the physics — would have made
> everything else worthless.

> 中文：**这是全场最重要的 90 秒。** 慢讲。
> 最后一段是论点，不是描述。停顿一下再讲最后一句。
> 如果时间被压缩到 5 分钟，保留这张。

---

### 5 · The closed loop — 60s

> Mechanically the loop is: propose, review, execute, score, gate. The optimizer
> suggests parameters; the safety gate checks them; six virtual instruments run in
> the order the YAML declares; only then do measurements become a single number;
> and only clean, successful runs feed back.
>
> The distinction I'd point at is on the left. Blocked is not the same as failed.
> A failure means a sample was consumed and produced nothing. A block means the
> gate refused to consume one at all. Those cost a real lab completely different
> amounts, so they're separate statuses and the benchmark reports them separately.
>
> And on the right — the guardrail fires at 440 degrees and 40 minutes, but samples
> don't actually degrade until 450 and 45. That's deliberate. A real lab doesn't
> know exactly where the cliff is, so the rule sits inside the uncertainty band.
> It costs the optimizer reachable search space, which is why blocked is reported
> as its own rate. Governance isn't free, and I'd rather the system show its price.

> 中文：**"Governance isn't free"** 是这场里最容易被记住的一句。
> 讲的时候手指向右边那张卡。这一张是你"懂实验室经济学"的证据。

---

### 6 · The benchmark — 60s

> Thirty seeds, thirty experiments each, Bayesian optimization against random
> search. BO reaches a median best of 0.818 against random's 0.724, and wins on
> twenty of the thirty seeds.
>
> Two things about the method. The comparison is paired — both methods draw the
> same per-experiment lab noise, so a per-seed comparison is actually meaningful.
> And every number on this slide comes out of one script and is written to an
> artifacts folder. Nothing here is typed by hand. The deck reads the same JSON
> the dashboard does.

> 中文：**"Nothing here is typed by hand"** 要说。
> 这句预防了「这个数你怎么知道是真的」这个问题——而且它是真的。

---

### 7 · Three things I say before I am asked — 75s ★

> These three are the caveats, and I'd rather say them than be asked.
>
> One — the bands overlap. BO wins in the median and on two seeds in three, but it
> doesn't dominate. On a five-dimensional landscape with a thirty-experiment
> budget, clean separation would actually be evidence that my benchmark was too
> easy.
>
> Two — BO is behind for the first ten experiments, because it's running its
> initial design. The advantage is sample efficiency later in the budget. A chart
> cropped at ten would tell the opposite story.
>
> Three — some runs exceed the ceiling line. That's not a bug. The line is the
> noise-free maximum, but the reported score is a noisy observation, so
> "best found so far" is an optimistically biased estimator. Taking a max over
> noisy draws captures luck. Any lab that ranks candidates on a single
> best-observed inherits that bias — which is why replication is a governance
> question, not a nicety.
>
> These three are printed in the dashboard and the README, not just in this deck.
> The honesty is in the product, not the pitch.

> 中文：这张是**分水岭**。
> 第三点（乐观有偏估计）是真正的技术深度信号——它说明你理解噪声下取最大值的统计
> 含义，而且能把它连回治理。
> 最后一句慢讲，是全场第二重的一句。

---

### 8 · Weights are a policy, not a constant — 60s

> How much is phase purity worth relative to efficiency? That's a research-strategy
> question, not a property of an XRD machine. So the weights live in versioned
> policy files, and every experiment records which policy scored it.
>
> Same optimizer, same surrogate, three policies. And the important caveat is at
> the bottom: **the median-best column is not comparable across these rows.** Each
> policy defines a different objective, so a higher number does not mean a better
> process. The comparable thing is the operating point — manufacturability-first
> converges on a treatment twelve minutes shorter and lighter doping. A visibly
> more conservative process.
>
> Treatment temperature lands near 388 under every policy, because that window
> dominates the landscape. Policy influences the parameters the objective leaves
> room to argue about.

> 中文：**主动说「这一列不可比」**。
> 一个不说这句话的人展示这张表，展示的是 bug；说了这句话，展示的是判断力。
> 最后那句关于 388°C 的观察，是"你真的看过数据"的证据。

---

### 9 · Published data, judgment kept visible — 60s

> The hydride side. The paper publishes lambda, omega-log, and an Allen-Dynes Tc.
> It publishes no score, no confidence, no feasibility. But ranking needs those —
> so I compute them from documented rules, and I keep them in separate files.
>
> Three tiers: published is a verbatim transcription. Derived is a documented
> transform of published values. Analyst is my judgment, encoded as a versioned
> rule set and labelled as judgment.
>
> The boundary is a file boundary, not a convention — and there's a test that
> fails if a score column ever appears in the published dataset. The reason is
> that this failure is silent: once my feasibility estimate sits in the same
> column family as a published lambda, nothing downstream can tell them apart, and
> in six months nobody remembers which was which.
>
> And the banner at the bottom is the honest headline: only one of twenty-two
> candidates has been refined beyond Allen-Dynes, and for that one, refinement
> moved 23.5 kelvin to 17. The authors call that an uncommon deviation.

> 中文：「provenance 是文件边界，不是约定」这句是**数据治理的核心论点**。
> 后面那句解释"为什么"——因为这个失效是静默的。这个理由比规则本身更有说服力。

---

### 10 · The finding a Tc-ordered list cannot show — 75s ★

> This is my favourite output, because it's the one a ranking sorted by predicted
> Tc structurally cannot produce.
>
> Ten of the twenty-two candidates contain technetium. It has no stable isotope —
> it's radioactive, and you'd need a licensed facility. That constraint is visible
> from the formula alone and completely invisible in any Tc-ordered list. It's also
> why feasibility combines as a minimum, not a mean: one disqualifying element
> isn't offset by three convenient ones.
>
> On the right, ranks move with the policy. EuCdH6Ru is second under high-Tc and
> ninth under lab-feasible. That swing is the warning label on every other row.
>
> Which is why the consensus shortlist is the useful output, not rank one. These
> three sit in the top five under every policy I considered — so they're what a lab
> validates regardless of whose priorities win the argument. That's the question a
> programme lead actually has to answer.

> 中文：**锝这个发现是全场最好讲的东西**——它是可验证的化学常识，不是模型输出，
> 任何人都能当场核对。而且它完全改变了对这批候选的看法。
> 最后一段把技术结论转成**项目管理语言**（"a programme lead actually has to answer"）。

---

### 11 · One system, not two demos — 60s

> A fair challenge at this point would be: those are two separate things in one
> repository. So this is the join.
>
> The selected candidate becomes a workflow that goes through the same parser and
> the same safety gate a CdTe experiment does — no orchestrator changes. And the
> gate blocked a hydride hazard it had never seen: 750 degrees with 150 bar
> hydrogen, both individually within bounds, refused on the combination. There's a
> test asserting that, because if it ever fails, the project has gone back to being
> two demos in one repository.
>
> Plans stop at "awaiting device implementation." There are no hydride synthesis
> devices and I won't fabricate any — simulating a hydrogenation anneal would be
> exactly the fake physics I refused earlier. The seam sits where a real lab's
> seam sits.

> 中文：**"A fair challenge at this point would be…"** ——主动提出对方可能的质疑，
> 然后回答它。这个技巧非常有效，它表明你预判了批评。

---

### 12 · Closing the loop — 90s ★

> That was the forward path. This is what comes back.
>
> Evidence is received, never manufactured. There are no hydride devices, so
> records enter from outside — an instrument, a collaborator, a paper. And a record
> with no named recorder or stated source is rejected at load: a measurement nobody
> will sign for can't overturn a prediction.
>
> Two judgments do the work here. The first is the one I care most about: a null
> result is meaningless without its measurement floor. One of these records saw no
> transition — but the rig only reached 8 kelvin and the prediction was 7.3. That
> experiment could not have observed the thing it was testing. So it's
> inconclusive, it's excluded from the calibration, and its hypothesis stays open.
> Counting it as agreement would quietly reward under-powered experiments.
>
> The second: evidence about one compound is evidence about the method.
> Twenty-one of twenty-two candidates rest on Allen-Dynes alone, so catching it
> running high on the one compound we measured bears on all of them. But — and this
> is the line I'd defend — a calibration lowers confidence and never rewrites a
> prediction. Producing a corrected Tc would invent a number nobody computed.
>
> And then the cohort re-ranks. The bit at the bottom is the one I didn't design.
> Measuring the leader low moved candidates nobody tested — because Tc is
> normalized against the best in the cohort, so when the leader falls, every
> untested compound becomes relatively more attractive. I only saw that by running
> it. A ranking is a statement about a set, not about a compound.

> 中文：最后一段要**放慢，并且承认这是意外发现**。
> "I only saw that by running it" —— 这句的价值在于它证明这是个**有行为的系统**，
> 不是一堆脚本。不要把它说成是你设计的。

---

### 13 · Bench Review — 45s

> One screen, because the loop has to meet a person somewhere.
>
> The approval queue is the hero of this layout, and that's the whole design
> argument: the held experiment is the only thing on the loop that needs a human.
> Proposing, executing, logging — none of those do. Putting approval anywhere but
> first would mean I'd missed why the screen exists.
>
> Every value on it is real system output. Sixty-pixel touch targets, no text
> entry, high contrast — it's a tablet at the bench, not a dashboard at a desk.
> I built it as a high-fidelity prototype rather than a React app, because a
> prototype is a product manager's deliverable. Building it in React would have
> demonstrated wanting to be a front-end engineer.

> 中文：最后一句是**主动回答"你为什么不做完整前端"**。
> 把一个看起来的短板转成职业定位的陈述。

---

### 14 · Five defects I found in my own build — 90s ★

> I'd rather spend time here than on anything that worked.
>
> These are five real defects, documented in the repo. I won't go through all of
> them — but the pattern is the point: **four of the five were silent.** The system
> looked correct while being wrong.
>
> The clearest one is the first. My safety gate protected nothing. Its hazard
> region was a strict subset of the true failure region, so every experiment it
> flagged was already doomed anyway. It prevented zero damage while appearing to
> work perfectly in every demo I ran. That's the characteristic failure mode of a
> governance layer — it looks identical whether or not it functions. The fix wasn't
> just widening the rule, it was adding a test that samples twenty thousand random
> points and asserts nothing degrading can reach a device.
>
> And the last one is my favourite. I rounded each weighted term to six decimal
> places — a change of one part in ten thousand. It moved the benchmark median by
> 0.006, because it changed which point the surrogate held as incumbent, which
> changed the argmax of Expected Improvement, and sent the whole search down a
> different path. The general lesson is that closed-loop systems are chaotically
> sensitive to their own numerics. Round for display, never before a decision.

> 中文：**这是你和其他候选人的最大差距。**
> 讲法：不要五个都讲，讲第 1 个和第 5 个，中间三个让幻灯片自己说。
> "I'd rather spend time here than on anything that worked" 这句开场很重要——
> 它把"承认错误"重构成"这才是值得看的部分"。
> 如果对方追问某一个，说明你成功了。

---

### 15 · What I deliberately did not build — 45s

> And the counterpart: what I chose not to build, with the reason for each.
>
> No physically accurate CdTe simulator, because that needs real process data and a
> fake physics model is worse than an honest surrogate. No hydride synthesis
> devices. No graphene use case — I considered it, but I had no grounded response
> model, and two defensible use cases beat three thin ones. No "correct" hydride
> ranking, because the paper publishes no scores and presenting one ranking as the
> answer would manufacture authority the data doesn't carry.
>
> In a real programme, deciding what not to build is most of the job.

> 中文：最后一句直接把 scope discipline 连到 PM 能力。
> 这张幻灯片的存在本身就是论点——**大多数 portfolio 只展示做了什么。**

---

### 16 · Why this, why me — 45s

> To close on where this fits.
>
> I'm not switching careers. I'm moving a proven delivery capability into a new
> domain. Life-science consulting taught me that a lab's bottleneck is usually its
> process and feedback loops rather than any single technique. Founding a company
> was a zero-to-one build under ambiguity, which is what this was, at smaller scale.
> And platform growth was about translating technical work into measurable impact,
> which is the research-to-impact translation this kind of role centres on.
>
> What the prototype adds is the domain-technical layer. The delivery capability
> was already there — what I needed to show is that I understand the closed loop,
> the data, and the governance well enough to run programmes in it.

> 中文：**不要在这里显得谦卑。** 这是陈述，不是请求。
> 「I'm optimizing for direction and team, not title」这句如果被问到 seniority，
> 就在这里用。

---

## If you only get 5 minutes

Cut to: **4 → 5 → 7 → 10 → 14 → 16.**

Honesty principle, the loop and what it refuses, the three caveats, the
technetium finding, the five defects, the close. That sequence still lands all
three of the things worth remembering.

> 中文：练熟这个 5 分钟版。它比 13 分钟版更常用——很多面试只给你 5 分钟展示，
> 剩下的时间是问答。

---

## Q&A prep

### "Is the CdTe simulator physically accurate?"
> No, and I never claim it is. It's a noisy surrogate benchmark environment with
> observation noise, a non-smooth process window, and failures. The claim isn't
> that I predict efficiency — it's that the system can execute, log, optimize and
> compare strategies under imperfect feedback.

### "Is BO only winning because your function is easy?"
> That's a fair worry for a smooth function. I added noise, an over-treatment
> cliff, invalid experiments, and ran thirty seeds under a fixed budget reporting
> median and IQR. And the bands overlap — I'd be more suspicious of my own
> benchmark if they didn't.

### "You hand-rolled the optimizer instead of using a library?"
> Deliberately. It's behind a two-method interface, so Ax or Optuna drops in
> without the orchestrator noticing. I kept a transparent GP with Expected
> Improvement because the project's purpose is to explain the loop — and that
> choice is exactly what let me find the optimizer getting trapped in failure
> regions. A black box would have hidden it.

### "Why are the hydride weights set that way?"
> They're decision policies, not constants. The dashboard switches between them
> live and shows the ranking move. And the honest output isn't rank one — it's the
> consensus shortlist, the candidates that survive every policy.

### "This is a programme management role. Why did you write code?"
> Not to prove I can engineer — my delivery record already covers execution. The
> gap this closes is domain credibility. I wanted to be able to say I understand
> where lab automation actually breaks, and the only way I know to earn that is to
> have broken it myself. Which I did, five times, and documented.

> 中文：这是最可能被问的问题之一。**答案的核心是「这个 portfolio 补的是领域可信度，
> 不是执行力」**——执行力你的履历已经证明了。不要显得像在申请工程师岗位。

### "How much of this did an AI write?"
> A lot of the code, and I'd say so on the record. I used coding assistants
> throughout. What I contributed is the part that determined whether it was worth
> anything: choosing two use cases that sit on opposite sides of the honesty line,
> refusing to fabricate the data the plan originally assumed the paper published,
> catching that the safety gate was protecting nothing, and deciding what not to
> build. The model will happily generate a hydride dataset with invented
> feasibility scores if you ask it to. Not asking is the job.

> 中文：**这个问题 2026 年一定会被问，必须有诚实答案。**
> 关键在于：不回避、不辩解，然后把价值重新定位到判断力上——而这正好就是 PM 岗位
> 要买的东西。最后一句 "Not asking is the job" 是整段的落点。
> 这个回答如果讲好，会比假装全是自己写的强得多。

### "What would you do differently?"
> I'd have written the benchmark script before writing anything into the README.
> The numbers in there were wrong for weeks — not fabricated, just stale and never
> re-derived. Making one script the only source of every published figure should
> have been the first decision, not a fix.

### "What's still missing?"
> Four of the eight planned tables, a per-experiment trace view, and the execution
> is synchronous rather than a real task queue. They're in the architecture doc
> under known gaps. None of them changes the argument, which is why I left them.

---

## Practice notes

> 中文：
> 1. **先对着幻灯片讲两遍，不要先录。** 卡壳的地方说明那张幻灯片的论证不顺——
>    改幻灯片比改视频便宜。
> 2. 讲者备注在 PowerPoint 里按「备注」能看到，每张都有。
> 3. 计时。第一遍大概率会超到 18-20 分钟，正常。砍的时候优先砍第 3、13、15 张。
> 4. 第 4、7、12、14 张不要砍，也不要赶。那是全部的差异化所在。
> 5. 录之前把第 16 张的 GitHub 链接换成真实地址。

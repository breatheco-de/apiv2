# https://wiki.archlinux.org/title/Main_page
FROM archlinux:base-devel
# FROM archlinux/archlinux:base-devel

RUN sed -i 's/#Color/Color/g' /etc/pacman.conf
RUN sed -i 's/NoProgressBar/#NoProgressBar/g' /etc/pacman.conf

RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm base-devel python python-pip python-virtualenv python-pipx curl \
    fish git sudo docker docker-compose fuse-overlayfs go postgresql libffi openssl \
    tk tcl zlib bzip2 xz sqlite reflector vi vim rsync redis \
    aws-cli gnu-netcat zip unzip less llvm clang pgcli nano


# RUN curl -sSL https://install.python-poetry.org | python3 -
# ENV PATH="/root/.local/bin:${PATH}"

RUN curl https://raw.githubusercontent.com/oh-my-fish/oh-my-fish/master/bin/install > install
RUN fish install --path=~/.local/share/omf --config=~/.config/omf --noninteractive
RUN echo "kernel.unprivileged_userns_clone=1" >> /etc/sysctl.conf
# RUN echo "vm.max_map_count=262144" >> /etc/sysctl.conf

# Set fish as default shell for root
RUN chsh -s /usr/bin/fish root

# Create rigo user and add to sudo and docker groups
RUN useradd -m rigo
# RUN usermod -aG sudo rigo
RUN usermod -aG docker rigo
RUN chsh -s /usr/bin/fish rigo

# Allow rigo to use sudo without password
RUN echo "rigo ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/rigo

USER rigo

WORKDIR /home/rigo

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/home/rigo/.local/bin:${PATH}"

RUN curl https://raw.githubusercontent.com/oh-my-fish/oh-my-fish/master/bin/install > install
RUN fish install --path=~/.local/share/omf --config=~/.config/omf --noninteractive

RUN git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si --noconfirm

RUN yay -S --noconfirm heroku-cli-bin

# RUN poetry install

# RUN poetry add poetry-dotenv-plugin

WORKDIR /home/rigo/apiv2

# COPY . .

COPY .devcontainer/postStartCommand.sh .devcontainer/postStartCommand.sh
COPY .devcontainer/onCreateCommand.sh .devcontainer/onCreateCommand.sh

RUN sudo chmod +x .devcontainer/postStartCommand.sh
RUN sudo chmod +x .devcontainer/onCreateCommand.sh

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY README.md README.md
COPY scripts scripts
COPY .python-version .python-version

RUN poetry python install $(cat ./.python-version)
RUN poetry env use $(cat ./.python-version)

RUN python -m scripts.install
COPY .devcontainer .devcontainer

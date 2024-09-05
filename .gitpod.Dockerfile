FROM gitpod/workspace-postgres:latest

SHELL ["/bin/bash", "-c"]

# Add LLVM repository and key
RUN wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add - \
    && echo "deb https://apt.llvm.org/jammy/ llvm-toolchain-jammy-18 main" | sudo tee /etc/apt/sources.list.d/llvm.list

RUN sudo apt-get update \
    && sudo apt-get install -y redis-server postgresql \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*



# That Gitpod install pyenv for me? no, thanks
# WORKDIR /home/gitpod/
# RUN rm .pyenv -Rf
# RUN rm .gp_pyenv.d -Rf
# RUN curl https://pyenv.run | bash


# RUN pyenv update && pyenv install 3.12.5 && pyenv global 3.12.5
RUN pyenv install 3.12.5 && pyenv global 3.12.5
RUN pip install pipenv yapf

# remove PIP_USER environment
USER gitpod
RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
RUN echo "" >> $HOME/.bashrc
RUN echo "unset DATABASE_URL" >> $HOME/.bashrc
RUN echo "export DATABASE_URL" >> $HOME/.bashrc
